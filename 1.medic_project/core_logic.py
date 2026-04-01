import hashlib
import cv2
import numpy as np
import easyocr
import streamlit as st
import os
from supabase import create_client, Client

# --- 1. Supabase Initialization ---
SUPABASE_URL = "https://kmmyznxttxhtwzvzjcaj.supabase.co"
SUPABASE_KEY = "sb_publishable_om3QNxTMb_Xlx6yLRFqmSg_4XonwDLE"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. Optimized OCR Loader (Fixes the "Downloading" Crash) ---
@st.cache_resource
def load_ocr_reader():
    # Ye sirf ek baar model download karega aur memory mein load rakhega
    return easyocr.Reader(['en'], gpu=False)

reader = load_ocr_reader()

def get_image_hash(image_path):
    hasher = hashlib.md5()
    with open(image_path, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

# --- 3. Advanced Feature Extraction ---
def analyze_medicine(image_path, actual_name):
    img = cv2.imread(image_path)
    if img is None: return None
    
    # Noise Reduction for better accuracy
    blurred = cv2.medianBlur(img, 5)
    
    # Color Detection (Simplified for now, can be expanded to HSV)
    h, w, _ = img.shape
    roi = img[h//3:2*h//3, w//3:2*w//3]
    avg_color = np.mean(roi)
    color_label = "White" if avg_color > 180 else "Colored"

    # Shape Detection (Robust logic)
    gray = cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY)
    edged = cv2.Canny(gray, 30, 150)
    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    shape_label = "Unknown"
    if contours:
        c = max(contours, key=cv2.contourArea)
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.04 * peri, True)
        x, y, w_r, h_r = cv2.boundingRect(c)
        aspect_ratio = float(w_r)/h_r
        
        if 0.9 <= aspect_ratio <= 1.1: shape_label = "Round"
        else: shape_label = "Capsule/Oval"

    # OCR Extraction
    results = reader.readtext(image_path)
    imprint = " ".join([res[1] for res in results]).lower().strip()

    return {"Color": color_label, "Shape": shape_label, "Imprint": imprint}

# --- 4. Automated Cloud Pipeline ---
def process_new_medicine(image_path, manual_name, medicine_use):
    clean_name = manual_name.lower().strip()
    img_hash = get_image_hash(image_path)

    # Duplicate Check
    check = supabase.table("inventory").select("name").eq("img_hash", img_hash).execute()
    if check.data:
        return False

    # Feature Extraction
    features = analyze_medicine(image_path, clean_name)
    if not features: return False

    # Upload to Supabase Storage
    file_ext = os.path.splitext(image_path)[1]
    cloud_filename = f"{clean_name.replace(' ', '_')}_{img_hash[:8]}{file_ext}"
    
    try:
        with open(image_path, 'rb') as f:
            supabase.storage.from_("medicine-images").upload(cloud_filename, f.read())
        
        img_url = supabase.storage.from_("medicine-images").get_public_url(cloud_filename)

        # Insert to SQL
        supabase.table("inventory").insert({
            "name": clean_name,
            "medicine_use": medicine_use.lower().strip(),
            "color": features['Color'],
            "shape": features['Shape'],
            "imprint": features['Imprint'],
            "img_url": img_url,
            "img_hash": img_hash
        }).execute()
        
        return True
    except Exception as e:
        st.error(f"Cloud Storage Error: {e}")
        return False
