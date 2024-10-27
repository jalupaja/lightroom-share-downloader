#!/usr/bin/env python3
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import requests
import os
import time
from concurrent.futures import ThreadPoolExecutor

print('Input your "lightroom.adobe.com/shares" link')
link = input(": ")

# CONFIG
export_file_type = ".jpeg"
output_folder = "output"
# wait time for the first 3 images (Page loading is often slower in the beginning)
wait_time_start = 2.5
# wait time for the all other images
wait_time_later = 0.5


def parse_url(url):
    driver = webdriver.Firefox()
    driver.get(url)
    page_source = driver.page_source
    driver.quit()
    return page_source


def download_image(url, file_name):
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        with open(f"{output_folder}/{file_name}{export_file_type}", "wb") as f:
            response.raw.decode_content = True
            for chunk in response.iter_content(chunk_size=1024):
                f.write(chunk)


def wait_for_first_image(class_str):
    first_image = None
    divs = None
    while first_image is None:
        # Wait for page loading
        divs = WebDriverWait(driver, 100).until(
            EC.presence_of_all_elements_located((By.TAG_NAME, "div"))
        )

        # get all divs which should have an image
        try:
            first_image = first_div_class_starts_with(divs, class_str)
        except:
            pass
    return divs, first_image


def first_div_class_starts_with(divs, str):
    for div in divs:
        if div.get_attribute("class") and div.get_attribute("class").startswith(str):
            return div
    return None


def div_class_starts_with(divs, str):
    return [
        div
        for div in divs
        if div.get_attribute("class") and div.get_attribute("class").startswith(str)
    ]


if not os.path.exists(output_folder):
    os.makedirs(output_folder)

driver = webdriver.Firefox()
driver.get(link)
tp = ThreadPoolExecutor(max_workers=5)

# TODO This will load infinitely if this page has no expected links...
_, first_image = wait_for_first_image("image")


urls = []
futures = []
export_name_counter = 0

first_image.click()

# go through all image
while True:
    # update export_name_counter
    export_name_counter += 1

    image_div = None
    while True:
        divs, image_div = wait_for_first_image("LoupeImage")
        # Wait for better image quality
        if export_name_counter <= 3:
            time.sleep(wait_time_start)
        else:
            time.sleep(wait_time_later)
        try:
            url = image_div.value_of_css_property("background-image")[5:-2]
        except:
            continue
        break
    print(f"Downloading {url}")

    urls.append(url)
    futures.append(
        tp.submit(
            download_image,
            url,
            f"image_{export_name_counter}",
        )
    )

    # get action buttons
    action_buttons = div_class_starts_with(divs, "ShareLoupeNextPrevControl")[
        0
    ].find_elements(By.TAG_NAME, "a")
    # btn_prev_image = action_buttons[1]
    btn_next_image = action_buttons[1]

    # if the next button has decreased opacity, all images should have been saved
    if btn_next_image.value_of_css_property("opacity") != "1":
        break
    btn_next_image.click()

driver.quit()

# Wait for downloads
for future in futures:
    future.result()
