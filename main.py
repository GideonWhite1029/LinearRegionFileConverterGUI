import dearpygui.dearpygui as dpg
import os
from multiprocessing import Manager
from glob import glob

from sources.convert_region_files import convert_file

def select_source_directory_callback(sender, app_data):
    dpg.set_value("source_dir", app_data['file_path_name'])

def select_destination_directory_callback(sender, app_data):
    dpg.set_value("destination_dir", app_data['file_path_name'])

def log_message(message, log_file=None):
    current_log = dpg.get_value("log_text")
    dpg.set_value("log_text", current_log + message + "\n")
    if log_file:
        with open(log_file, "a") as f:
            f.write(message + "\n")

def convert_files_callback(sender, app_data, user_data):
    source_dir = dpg.get_value("source_dir")
    destination_dir = dpg.get_value("destination_dir")
    conversion_mode = dpg.get_value("conversion_mode")
    compression_level = dpg.get_value("compression_level")
    log = dpg.get_value("log")

    log_file = None
    if log:
        log_file = os.path.join(os.path.dirname(__file__), "conversion_log.txt")
        log_message("Logging enabled. Log file: " + log_file, log_file)

    file_ext = "*.linear" if conversion_mode == "linear2mca" else "*.mca"
    file_list = glob(os.path.join(source_dir, file_ext))
    log_message(f"Found {len(file_list)} region files to convert", log_file)

    with Manager() as manager:
        converted_counter = manager.Value("i", 0)
        skipped_counter = manager.Value("i", 0)
        total_files = len(file_list)
        for index, file in enumerate(file_list):
            convert_file((file, conversion_mode, destination_dir, compression_level, converted_counter, skipped_counter, log))
            progress = (index + 1) / total_files
            percentage = progress * 100
            dpg.set_value("progress_bar", progress)
            dpg.set_value("progress_bar_text", f"Progress: {percentage:.2f}%")
        log_message(f"Conversion complete: {converted_counter.value} region files converted, {skipped_counter.value} region files skipped", log_file)

dpg.create_context()

font_path = os.path.join(os.path.dirname(__file__), "font/DejaVuSans.ttf")

with dpg.font_registry():
    with dpg.font(font_path, 20) as default_font:
        dpg.add_font_range_hint(dpg.mvFontRangeHint_Cyrillic)

dpg.bind_font(default_font)

with dpg.window(label="Linear Region File Converter", width=800, height=600):
    dpg.add_input_text(label="Source Directory", tag="source_dir", readonly=True)
    dpg.add_button(label="Select Source Directory", callback=lambda: dpg.show_item("source_dir_dialog"))
    dpg.add_input_text(label="Destination Directory", tag="destination_dir", readonly=True)
    dpg.add_button(label="Select Destination Directory", callback=lambda: dpg.show_item("destination_dir_dialog"))
    dpg.add_combo(label="Conversion Mode", items=["mca2linear", "linear2mca"], tag="conversion_mode")
    dpg.add_slider_int(label="Compression Level", default_value=6, min_value=1, max_value=22, tag="compression_level")
    dpg.add_checkbox(label="Log", tag="log")
    dpg.add_button(label="Convert Files", callback=convert_files_callback)
    dpg.add_text("Progress Bar: ")
    dpg.add_progress_bar(label="Progress", tag="progress_bar", default_value=0.0)
    dpg.add_text("", tag="progress_bar_text")
    dpg.add_text("", tag="log_text")

with dpg.file_dialog(directory_selector=True, show=False, callback=select_source_directory_callback, tag="source_dir_dialog"):
    dpg.add_file_extension(".*")

with dpg.file_dialog(directory_selector=True, show=False, callback=select_destination_directory_callback, tag="destination_dir_dialog"):
    dpg.add_file_extension(".*")

dpg.create_viewport(title='Linear Region File Converter', width=800, height=600)
dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()