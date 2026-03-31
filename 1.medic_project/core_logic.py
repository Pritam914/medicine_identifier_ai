import sqlite3
import os
import hashlib
import cv2
import numpy as np
import easyocr
import shutil

# Initialize OCR once (EasyOCR reader initialization)
reader = easyocr.Reader(['en'], gpu=False)

def get_image_hash(image_path):
    """Image ka unique fingerprint nikalna (Duplicate prevention ke liye)."""
    hasher = hashlib.md5()
    with open(image_path, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def organize_and_save(image_path, medicine_name):
    """Images ko processed folder mein unique name ke sath save karna."""
    target_dir = r'C:\Users\PRITAM\1.medic_project\dataset\processed_images'
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    
    file_extension = os.path.splitext(image_path)[1]
    # Name se spaces hata kar underscore lagana
    safe_name = medicine_name.replace(' ', '_')
    new_filename = f"{safe_name}_{get_image_hash(image_path)[:8]}{file_extension}"
    final_path = os.path.join(target_dir, new_filename)
    
    shutil.copy(image_path, final_path)
    return final_path

def analyze_medicine(image_path, actual_name):
    """Pill features (Color, Shape, Text) extract karne ka main function."""
    img = cv2.imread(image_path)
    if img is None: return None
    
    # 1. Color Extraction
    h, w, _ = img.shape
    roi = img[h//2-10:h//2+10, w//2-10:w//2+10]
    avg_color = np.average(np.average(roi, axis=0), axis=0)
    color_label = "White" if np.mean(avg_color) > 180 else "Colored"

    # 2. Shape Detection (Restored Logic)
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

    # 3. OCR (Text)
    results = reader.readtext(gray)
    imprint_text = " ".join([str(res[1]) for res in results]).strip()

    return {
        "Medicine_Name": actual_name,
        "Color": color_label,
        "Shape": shape_label,
        "Imprint": imprint_text
    }

def process_new_medicine(image_path, manual_name):
    """Database insertion with cleaned names and duplicate check."""
    # Step 1: Standardize name (Lower case and trim)
    clean_name = manual_name.lower().strip() 

    conn = sqlite3.connect('medic_vault.db')
    cursor = conn.cursor()

    # Table ensure karna (img_hash column ke saath)
    cursor.execute('''CREATE TABLE IF NOT EXISTS inventory 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT,
                       name TEXT, color TEXT, shape TEXT, 
                       imprint TEXT, img_path TEXT, 
                       img_hash TEXT UNIQUE, 
                       is_trained INTEGER DEFAULT 0)''')
    
    # Step 2: Duplicate Check
    current_hash = get_image_hash(image_path)
    try:
        cursor.execute("SELECT name FROM inventory WHERE img_hash = ?", (current_hash,))
        if cursor.fetchone():
            print(f"⚠️ Already exists: {clean_name}")
            conn.close()
            return False
    except sqlite3.OperationalError:
        # Agar purani table mein img_hash nahi hai toh reset alert
        print("🚨 Database Error: Please delete 'medic_vault.db' file manually once.")
        conn.close()
        return False

    # Step 3: Analyze and Save
    data = analyze_medicine(image_path, clean_name) # clean_name pass kiya
    if data:
        final_path = organize_and_save(image_path, clean_name)
        cursor.execute("""INSERT INTO inventory (name, color, shape, imprint, img_path, img_hash) 
                          VALUES (?, ?, ?, ?, ?, ?)""", 
                       (clean_name, data['Color'], data['Shape'], 
                        data['Imprint'], final_path, current_hash))
        conn.commit()
        print(f"✅ Processed: {clean_name}")
        
    conn.close()
    return True