import sys
import os
import json
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
import rasterio
import geopandas as gpd
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import requests

# ============================================================
# ENV + API INIT
# ============================================================
load_dotenv()

try:
    project_root = Path(__file__).resolve().parent
except NameError:
    project_root = Path().resolve()

libs_path = project_root / "libs" / "scoutmaster_api"
sys.path.insert(0, str(libs_path))

from scoutmaster.api import ScoutMasterAPI

client_id = os.getenv("SM_CLIENT_ID")
client_secret = os.getenv("SM_CLIENT_SECRET")

SM_API = ScoutMasterAPI(version="v3")
SM_API.authenticate(client_id=client_id, client_secret=client_secret)


# ============================================================
# CONFIG
# ============================================================
LAYER_TYPE_ID = "0685e79a-d5ca-43f8-a634-6068bdbacfab"
HARVEST_VARIATION_LAYER_TYPE_ID = "a4c30c51-0623-415e-b569-38d43d99d89a"
PROJECT_ID = "2110f1eb-25fd-439c-aafb-de46e50824e5"

TEMP_DIR = Path("./tmp_uploads")
TEMP_DIR.mkdir(exist_ok=True)

LOG_DIR = Path("./logs")
LOG_DIR.mkdir(exist_ok=True)


# ============================================================
# MODEL
# ============================================================
def logistic4(x, A, K, r, T0):
    return A + (K - A) / (1 + np.exp(-r * (x - T0)))


# ============================================================
# ALREADY PROCESSED CHECK
# ============================================================
def already_has_harvest_map(SM_API, field_id):
    try:
        layers = SM_API.layers(field_id=field_id, layer_type_id=HARVEST_VARIATION_LAYER_TYPE_ID)
        return layers is not None and not layers.empty
    except:
        return False


# ============================================================
# WDVI
# ============================================================
def mean_wdvi_from_path(file_path):
    try:
        parsed = urlparse(file_path)
        ext = Path(parsed.path).suffix.lower().replace(".", "")

        if ext in ["tif", "tiff"]:
            with rasterio.open(file_path) as src:
                data = src.read(1, masked=True)
                if np.ma.count(data) == 0:
                    return None
                return float(data.mean())

        if ext == "geojson":
            gdf = gpd.read_file(file_path)
            if "DN" not in gdf.columns:
                return None
            return float(pd.to_numeric(gdf["DN"], errors="coerce").mean())

    except Exception as e:
        print("❌ WDVI error:", e)
        return None

    return None


# ============================================================
# TSUM
# ============================================================
def get_tsum_series(SM_API, cultivation_id):
    print(f"   → TSUM {cultivation_id}")

    try:
        df = SM_API.cultivations_tsum(cultivation_id)
    except Exception as e:
        print("❌ TSUM API failed:", e)
        return None

    if df is None or df.empty:
        return None

    if "value" in df.columns:
        df = df.rename(columns={"value": "tsum"})
    elif "tsum" not in df.columns:
        return None

    if "date" not in df.columns:
        return None

    df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
    df = df.dropna(subset=["date"])
    df["date"] = df["date"].dt.tz_convert(None)

    return df.sort_values("date")


def tsum_at_date(df_tsum, cultivation_id, acquired_at):
    df = df_tsum[df_tsum["cultivation_id"] == cultivation_id]
    if df.empty:
        return None

    acquired_at = pd.to_datetime(acquired_at)

    # timezone fix
    if getattr(acquired_at, "tzinfo", None):
        acquired_at = acquired_at.tz_convert(None)

    df = df[df["date"] <= acquired_at]
    if df.empty:
        return None

    return float(df.iloc[-1]["tsum"])


# ============================================================
# UPLOAD HARVEST VARIATION
# ============================================================
def upload_harvest_variation(SM_API, row, field_id):
    print("   ⬆️ uploading harvest variation")

    local_path = None

    try:
        parsed = urlparse(row["path"])
        ext = Path(parsed.path).suffix
        file_name = f"{field_id}_{row['acquired_at'].strftime('%Y%m%d')}{ext}"
        local_path = TEMP_DIR / file_name

        r = requests.get(row["path"], stream=True)
        r.raise_for_status()

        with open(local_path, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)

        acquired_at_clean = pd.to_datetime(row["acquired_at"]).strftime("%Y-%m-%dT%H:%M:%SZ")

        SM_API.layer_create(
            field_id=field_id,
            type_id=HARVEST_VARIATION_LAYER_TYPE_ID,
            acquired_at=acquired_at_clean,
            file_path=str(local_path)
        )

        print("   ✅ upload success")

    except Exception as e:
        print("   ❌ upload failed:", e)

    finally:
        if local_path and local_path.exists():
            local_path.unlink()


# ============================================================
# PATCH INFLECTION EVENT
# ============================================================
def patch_inflection_event(SM_API, cultivation_id, existing_events, inflection_date):
    print("   📅 patching inflection event")

    try:
        # parse existing events safely
        if isinstance(existing_events, str):
            events = json.loads(existing_events)
        elif existing_events is None:
            events = []
        else:
            events = list(existing_events)

        # skip if already patched
        if any(e.get("type") == "inflection_point" for e in events):
            print("   ⏩ inflection event already exists → SKIP")
            return

        # append inflection event
        events.append({
            "type": "inflection_point",
            "date": pd.to_datetime(inflection_date).strftime("%Y-%m-%dT%H:%M:%SZ")
        })

        response = requests.patch(
            f"{SM_API.host}/v3/calendars/{cultivation_id}",
            headers=SM_API._get_headers(),
            json={"events": events}
        )

        response.raise_for_status()
        print("   ✅ patch success")

    except Exception as e:
        print("   ❌ patch failed:", e)


# ============================================================
# CLEAN
# ============================================================
def clean_df(df):
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=["tsum", "wdvi"])

    df = df.groupby("tsum", as_index=False).agg({
        "wdvi": "mean",
        "acquired_at": "first",
        "path": "first"
    })

    return df.sort_values("tsum")


# ============================================================
# FIT
# ============================================================
def fit_model(df):
    x = df["tsum"].to_numpy(float)
    y = df["wdvi"].to_numpy(float)

    A0 = np.percentile(y, 10)
    K0 = np.percentile(y, 90)

    try:
        popt, _ = curve_fit(
            logistic4,
            x, y,
            p0=[A0, K0, 0.01, np.median(x)],
            maxfev=100000
        )
        return popt
    except:
        return None


# ============================================================
# START
# ============================================================
print(f"🚀 PIPELINE STARTED — {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")

df_cult = SM_API.cultivations(PROJECT_ID)
print(f"📦 cultivations: {len(df_cult)}")

all_rows = []

# ============================================================
# STEP 1 — build dataset
# ============================================================
print("\n🔵 STEP 1")

for _, c in df_cult.iterrows():

    field_id = c["field_id"]
    field_name = c["field_name"]

    print("\nFIELD:", field_name)

    if already_has_harvest_map(SM_API, field_id):
        print("   ⏩ already has harvest map → SKIP")
        continue

    try:
        df_layers = SM_API.layers(
            field_id=field_id,
            layer_type_id=LAYER_TYPE_ID
        )

        if df_layers is None or df_layers.empty:
            print("   ⚠️ no layers")
            continue

        df_layers["acquired_at"] = pd.to_datetime(df_layers["acquired_at"], utc=True).dt.tz_convert(None)

        df_tsum = get_tsum_series(SM_API, c["id"])
        if df_tsum is None:
            continue

        df_tsum["cultivation_id"] = c["id"]

        crop = c["crop"]
        crop = crop["name"] if isinstance(crop, dict) else str(crop)

        for _, r in df_layers.iterrows():

            wdvi = mean_wdvi_from_path(r["path"])
            tsum = tsum_at_date(df_tsum, c["id"], r["acquired_at"])

            if wdvi is None or tsum is None:
                continue

            all_rows.append({
                "field_id": field_id,
                "crop": crop,
                "tsum": tsum,
                "wdvi": wdvi,
                "acquired_at": r["acquired_at"],
                "path": r["path"]
            })

        print("   ✅ samples collected")

    except Exception as e:
        print("❌ FIELD ERROR:", e)


# ============================================================
# STEP 2 — crop-level priors
# ============================================================
print("\n🟡 STEP 2")

df_all = pd.DataFrame(all_rows)

priors = []

for crop, g in df_all.groupby("crop"):
    print("   → crop:", crop)

    fit = fit_model(g)
    if fit is None:
        continue

    A, K, r, T0 = fit
    priors.append({"crop": crop, "A": A, "K": K, "r": r, "T0": T0})

df_priors = pd.DataFrame(priors)
print(f"✅ priors: {len(df_priors)}")


# ============================================================
# STEP 3 — per-field fit + upload + patch
# ============================================================
print("\n🟢 STEP 3")

for _, c in df_cult.iterrows():

    field_id = c["field_id"]
    field_name = c["field_name"]

    print("\nFIELD:", field_name)

    if already_has_harvest_map(SM_API, field_id):
        print("   ⏩ already processed")
        continue

    crop = c["crop"]
    crop = crop["name"] if isinstance(crop, dict) else str(crop)

    prior = df_priors[df_priors["crop"] == crop]
    if prior.empty:
        print("   ⚠️ no prior for crop:", crop)
        continue

    df_field = pd.DataFrame([r for r in all_rows if r["field_id"] == field_id])

    if len(df_field) < 6:
        print("   ⚠️ not enough data")
        continue

    df_field = clean_df(df_field)

    fit = fit_model(df_field)
    if fit is None:
        print("   ⚠️ fit failed")
        continue

    A, K, r, T0 = fit

    print(f"   📈 T0 = {T0:.2f}  |  current TSUM max = {df_field['tsum'].max():.2f}")

    if df_field["tsum"].max() >= T0:
        print("   🔥 INFLECTION DETECTED")

        closest = df_field.iloc[(df_field["tsum"] - T0).abs().argmin()]
        inflection_date = closest["acquired_at"]

        # upload harvest variation layer
        upload_harvest_variation(SM_API, closest, field_id)

        # patch inflection event to calendar
        patch_inflection_event(SM_API, c["id"], c["events"], inflection_date)

    else:
        print("   ⏳ not yet past inflection")

print(f"\n✅ DONE — {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")