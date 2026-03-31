import os
import hashlib
import cv2
import numpy as np
import easyocr
from supabase import create_client, Client

# --- Supabase Credentials ---
SUPABASE_URL = "https://kmmyznxttxhtwzvzjcaj.supabase.co"
SUPABASE_KEY = "sb_publishable_om3QNxTMb_Xlx6yLRFqmSg_4XonwDLE"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

reader = easyocr.Reader(['en'], gpu=False)

def get_image_hash(image_path):
    hasher = hashlib.md5()
    with open(image_path, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def analyze_medicine(image_path, actual_name):
    img = cv2.imread(image_path)
    if img is None: return None
    
    # 1. Color Extraction
    h, w, _ = img.shape
    roi = img[h//2-10:h//2+10, w//2-10:w//2+10]
    avg_color = np.average(np.average(roi, axis=0), axis=0)
    color_label = "White" if np.mean(avg_color) > 180 else "Colored"

    # 2. Shape Detection
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 30, 150)
    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    shape_label = "Unknown"
    if contours:
        c = max(contours, key=cv2.contourArea)
        x, y, w_rect, h_rect = cv2.boundingRect(c)
        aspect_ratio = float(w_rect)/h_rect
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.03 * peri, True)
        if 0.9 <= aspect_ratio <= 1.1 and len(approx) > 6: shape_label = "Round"
        elif aspect_ratio > 1.2 or aspect_ratio < 0.8: shape_label = "Capsule/Oval"
        else: shape_label = "Rectangular/Other"

    # 3. OCR
    results = reader.readtext(gray)
    imprint_text = " ".join([str(res[1]) for res in results]).strip()

    return {"Color": color_label, "Shape": shape_label, "Imprint": imprint_text}

def process_new_medicine(image_path, manual_name):
    clean_name = manual_name.lower().strip()
    img_hash = get_image_hash(image_path)

    # 1. Duplicate Check (Cloud)
    check = supabase.table("inventory").select("name").eq("img_hash", img_hash).execute()
    if check.data:
        return False

    # 2. Analyze Features
    features = analyze_medicine(image_path, clean_name)
    if not features: return False

    # 3. Upload to Supabase Storage
    file_ext = os.path.splitext(image_path)[1]
    cloud_filename = f"{clean_name.replace(' ', '_')}_{img_hash[:8]}{file_ext}"
    
    with open(image_path, 'rb') as f:
        supabase.storage.from_("medicine-images").upload(cloud_filename, f.read())
    
    img_url = supabase.storage.from_("medicine-images").get_public_url(cloud_filename)

    # 4. Insert to Cloud Database
    supabase.table("inventory").insert({
        "name": clean_name,
        "color": features['Color'],
        "shape": features['Shape'],
        "imprint": features['Imprint'],
        "img_url": img_url,
        "img_hash": img_hash
    }).execute()
    
    return True
