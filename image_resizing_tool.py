from PIL import Image
import os
import glob

root = './original_images/'
folders = next(os.walk(root))[1]

for folder in folders:
    print('processing', folder)
    files = glob.glob(root + folder + '/*.png')
    for file in files:
        image = Image.open(file)
        x, y = image.size
        if x > y:
            crop_val = (x - y) / 2
            image = image.crop((crop_val, 0, x - crop_val, y))
        else:
            crop_val = (y - x) / 2
            image = image.crop((0, crop_val, x, y - crop_val))
        image = image.resize((256, 256))
        image.save(file)
