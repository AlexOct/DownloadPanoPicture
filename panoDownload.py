
import urllib.request
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import math
import sys

def download(url, path, name):
    file_path = os.path.join(path, name)
    if os.path.exists(file_path):
        print(f"File {name} already exists, skipping download.")
        return file_path
    try:
        response = urllib.request.urlopen(url)
        content = response.read()
        os.makedirs(path, exist_ok=True)
        with open(file_path, 'wb') as file:
            file.write(content)
        print(f"Downloaded {name} to {path}, size: {len(content)} bytes")
        return file_path 
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return None
######################potree#################################
def process_panorama_list_potree(input_file, base_url, output_dir):
    try:
        with open(input_file, 'r') as fp:
            lines = fp.readlines() 
    except FileNotFoundError:
        print(f"File not found: {input_file}")
        return
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        downloaded_images = []
        for line in lines:
            if line.startswith("File") or line.strip() == "":
                continue
            parts = line.split()
            if len(parts) < 8:
                print(f"Invalid line format: {line}")
                continue
            relative_path = parts[0].strip('"') 
            file_name = os.path.basename(relative_path)
            download_url = f"{base_url}/{relative_path}"
            future = executor.submit(download, download_url, output_dir, file_name)
            futures.append(future)
        for future in as_completed(futures):
            result = future.result()
            if result:
                downloaded_images.append(result)
        print(f"Downloaded {len(downloaded_images)} files successfully.")

##################potree##################################
PIL_INSTALLED = False
try:
    sys.path.append(r'C:\Users\site-packages')
    from PIL import Image # 需要下载,pip install Pillow ，注意下载位置如果无法直接导入,用上面这句话设置到下载的路径
    import numpy as np# 需要下载,pip install Numpy
    import re
    PIL_INSTALLED = True
except ImportError:
    print("Pillow or numpy is not installed. Skipping 'process_panorama_list_baidu' execution.")
    PIL_INSTALLED = False
    
def get_coordinates_from_filename(file_path):
    filename = file_path.split('\\')[-1]
    match = re.match(r"(\d+)_(\d+)_z(\d+)\.jpg", filename)
    if match:
        x, y = int(match.group(1)), int(match.group(2))
        return x, y
    else:
        print(f"Warning: Invalid filename format: {filename}")
        return 0, 0

def create_pano_image(image_paths, rows, cols, output_dir):
    images = []
    for img_path in image_paths:
        try:
            img = Image.open(img_path)
            images.append(img)
        except Exception as e:
            print(f"Failed to open image {img_path}: {e}")
    if not images:
        print("No images to stitch.")
        return
    img_width, img_height = images[0].size
    pano_width = img_width * cols
    pano_height = img_height * rows//2
    pano_image = Image.new('RGB', (pano_width, pano_height))
    for i in range(rows):
        for j in range(cols):
            index = i * cols + j
            if index < len(images):
                pano_image.paste(images[index], (j * img_width, i * img_height))
    output_path = os.path.join(output_dir, 'pano_image.jpg')
    pano_image.save(output_path)
    print(f"Panorama image saved to: {output_path}")
    generate_cube_map(output_path,output_dir);

def process_face(i, im, face_size, output_dir):
    color_side = Image.new("RGB", (face_size, face_size))
    pixels = color_side.load()
    im_width, im_height = im.size
    HSIZE = face_size / 2.0
    for axA in range(face_size):
        for axB in range(face_size):
            z = -axA + HSIZE
            if i == 0:  # front
                x = HSIZE
                y = -axB + HSIZE
            elif i == 1:  # back
                x = -HSIZE
                y = axB - HSIZE
            elif i == 2:  # left
                x = axB - HSIZE
                y = HSIZE
            elif i == 3:  # right
                x = -axB + HSIZE
                y = -HSIZE
            elif i == 4:  # top
                z = HSIZE
                x = axB - HSIZE
                y = axA - HSIZE
            elif i == 5:  # bottom
                z = -HSIZE
                x = axB - HSIZE
                y = -axA + HSIZE

            # Convert cartesian coordinates to spherical coordinates
            r = math.sqrt(float(x*x + y*y + z*z))
            theta = math.acos(float(z)/r)
            phi = -math.atan2(float(y), x)
            
            # Map spherical coordinates to the equirectangular projection
            ix = int((im_width - 1) * phi / (2 * math.pi))
            iy = int((im_height - 1) * (theta) / math.pi)

            # Get RGB values from the equirectangular image
            r, g, b = im.getpixel((ix, iy))

            if i == 5:  # bottom
                pixels[axA,-axB] = (r, g, b)
            elif i == 4:  # top
                pixels[-axA,axB] = (r, g, b)
            else:
            # Set the pixel in the cube map face
                pixels[axB,axA] = (r, g, b)
    face_names = ['front', 'back', 'left', 'right', 'top', 'bottom']
    color_side.save(os.path.join(output_dir, f"{face_names[i]}.jpg"), quality=85)

def generate_cube_map(pano_image_path, output_dir):
    try:
        pano_image = Image.open(pano_image_path)
        pano_width, pano_height = pano_image.size
        if pano_height != pano_width // 2:
            print("Expected panorama image to be 2:1 aspect ratio (width x height).")
            return
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        face_size = pano_width // 4
        for i in range(6):
            process_face( i ,pano_image ,face_size,output_dir) 
        print("Skybox images saved to:", output_dir)
    except Exception as e:
        print(f"Error processing panorama: {e}")
        
BASE_URL = "https://mapsv1.bdimg.com/?qt=pdata&sid={sid}"
def process_panorama_list_baidu(file_path, output_dir):
    try:
        with open(file_path, "r") as fp:
            sids = [line.strip() for line in fp.readlines()]
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return
    with ThreadPoolExecutor(max_workers=10) as executor:
        for sid  in sids:
            futures = []
            downloaded_images = []  
            row_max = 8 
            col_max = 8
            if not sid:
                return  
            pano_dir = os.path.join(output_dir, sid)
            for row in range(row_max):
                for col in range(col_max):
                    z = '4'
                    y = str(row)
                    x = str(col)
                    url = f"{BASE_URL.format(sid=sid)}&pos={y}_{x}&z={z}"
                    path = pano_dir
                    name = f"{y}_{x}_z{z}.jpg"
                    print(f"Submitting download task for: {url}")
                    future = executor.submit(download, url, path, name)
                    futures.append(future)

            for future in as_completed(futures):
                result = future.result() 
                if result:
                    downloaded_images.append(result)
    
            downloaded_images.sort(key=lambda x: get_coordinates_from_filename(x))
            if downloaded_images:
                create_pano_image(downloaded_images, 8, 8, pano_dir)  # 行列都为 8

def generate_panolist(file_path, data):
    try:
        with open(file_path, 'w') as file:
            for line in data:
                file.write(line + '\n')
        print(f"File {file_path} created successfully!")
    except Exception as e:
        print(f"Failed to create {file_path}: {e}")

##############################################################

if __name__ == "__main__":
    output_dir_potree = r"E:\\potree360Test2"
    output_dir_baidu = r"E:\\baidumap2"

    base_url = "http://5.9.65.151/mschuetz/potree/resources/pointclouds/helimap/360/Drive2_selection"
    coordinates_file_name = "coordinates.txt"
    coordinates_path = download(f"{base_url}/{coordinates_file_name}", output_dir_potree, coordinates_file_name)
    process_panorama_list_potree(coordinates_path,base_url, output_dir_potree)
    input_file_baidu = os.path.join(output_dir_baidu,  "panolist.txt")
    data = [
        "09002200011706150924439322B",
        "09002200011706150924458182B",
        "09002200011706150924471772B",
        "09002200011706150924490692B",
        "09002200011706150924522692B",
        "09002200011706150924552322B",
        "09002200011706150924579352B",
        "09002200011706150925028382B"
    ]
    generate_panolist(input_file_baidu,data)
    if(PIL_INSTALLED):
        process_panorama_list_baidu(input_file_baidu , output_dir_baidu)
