import os
import hashlib
import cv2
import numpy as np
import easyocr
import streamlit as st
from supabase import create_client, Client

# --- 1. Supabase Initialization ---
SUPABASE_URL = "https://kmmyznxttxhtwzvzjcaj.supabase.co"
# Note: Security ke liye Key ko environment variable mein rakhna behtar hai
SUPABASE_KEY = "sb_publishable_om3QNxTMb_Xlx6yLRFqmSg_4XonwDLE" 
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. Efficient Model Loading ---
@st.cache_resource
def load_ocr_reader():
    """OCR model ko memory mein cache karta hai taaki har upload par load na ho."""
    return easyocr.Reader(['en'], gpu=False)

reader = load_ocr_reader()

# --- 3. Image Analysis Functions ---

def get_image_hash(image_path):
    """Duplicate images ko rokne ke liye unique hash generate karta hai."""
    hasher = hashlib.md5()
    with open(image_path, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def detect_actual_color(img):
    """HSV color space ka use karke medicine ka primary color pehchanta hai."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Range definitions (H, S, V)
    colors = {
        "Red": ([0, 120, 70], [10, 255, 255]),
        "Blue": ([100, 150, 0], [140, 255, 255]),
        "Green": ([35, 100, 100], [85, 255, 255]),
        "Yellow": ([20, 100, 100], [30, 255, 255]),
        "White": ([0, 0, 180], [180, 50, 255]),
        "Pink/Purple": ([140, 50, 50], [170, 255, 255])
    }
    
    max_pixels = 0
    final_color = "Colored"
    
    # Background noise hatane ke liye center 1/3 area par focus
    h, w, _ = img.shape
    center_roi = hsv[h//3:2*h//3, w//3:2*w//3]

    for color_name, (lower, upper) in colors.items():
        mask = cv2.inRange(center_roi, np.array(lower), np.array(upper))
        pixels = cv2.countNonZero(mask)
        if pixels > max_pixels:
            max_pixels = pixels
            final_color = color_name
            
    return final_color

def analyze_medicine(image_path):
    """Computer Vision ka use karke Color, Shape aur Imprint extract karta hai."""
    img = cv2.imread(image_path)
    if img is None: return None
    
    # Noise reduction
    blurred = cv2.medianBlur(img, 5)

    # 1. Color
    color_label = detect_actual_color(blurred)

    # 2. Shape (Circularity Logic)
    gray = cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    shape_label = "Unknown"
    if contours:
        c = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(c)
        perimeter = cv2.arcLength(c, True)
        
        if area > 100:
            x, y, w_rect, h_rect = cv2.boundingRect(c)
            aspect_ratio = float(w_rect)/h_rect
            circularity = (4 * np.pi * area) / (perimeter * perimeter) if perimeter > 0 else 0
            
            if circularity > 0.8: shape_label = "Round"
            elif aspect_ratio > 1.2 or aspect_ratio < 0.8: shape_label = "Capsule/Oval"
            else: shape_label = "Rectangular/Other"

    # 3. OCR (Text Extraction)
    results = reader.readtext(gray)
    imprint_text = " ".join([str(res[1]) for res in results]).lower().strip()

    return {"Color": color_label, "Shape": shape_label, "Imprint": imprint_text}

# --- 4. Main Process Function ---

def process_new_medicine(image_path, manual_name, medicine_use):
    """
    Backend Entry Point:
    1. Duplicate check karta hai.
    2. Image analyze karta hai.
    3. Storage aur Database update karta hai.
    """
    clean_name = manual_name.lower().strip()
    img_hash = get_image_hash(image_path)

    # 1. Multi-admin/user Duplicate Check (Based on Image Hash)
    check = supabase.table("inventory").select("name").eq("img_hash", img_hash).execute()
    if check.data: 
        return False # Medicine already exists

    # 2. Extract Features
    features = analyze_medicine(image_path)
    if not features: 
        return False

    # 3. Cloud Storage Upload
    try:
        file_ext = os.path.splitext(image_path)[1]
        # Unique filename using hash to avoid overwriting
        cloud_filename = f"{clean_name.replace(' ', '_')}_{img_hash[:8]}{file_ext}"
        
        with open(image_path, 'rb') as f:
            supabase.storage.from_("medicine-images").upload(cloud_filename, f.read())
        
        img_url = supabase.storage.from_("medicine-images").get_public_url(cloud_filename)

        # 4. Database Insertion
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
        print(f"Error in process_new_medicine: {e}")
        return False
