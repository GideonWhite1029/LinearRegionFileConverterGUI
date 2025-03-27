import dearpygui.dearpygui as dpg
import os
from multiprocessing import Manager, Pool, cpu_count, Event
from glob import glob

from sources.convert_region_files import convert_file

stop_event = Event()

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

def process_file_wrapper(args):
    file, conversion_mode, destination_dir, compression_level, log_enabled, log_file = args

    try:
        local_converted = 0
        local_skipped = 0

        if stop_event.is_set():
            return (0, 1, file)

        convert_file((file, conversion_mode, destination_dir, compression_level,
                      local_converted, local_skipped, log_enabled))

        return (local_converted, local_skipped, file)
    except Exception as e:
        error_message = f"Error processing file {file}: {str(e)}"
        if log_enabled and log_file:
            with open(log_file, "a") as f:
                f.write(error_message + "\n")
        return (0, 1, file)

def convert_files_callback(sender, app_data, user_data):
    global stop_event
    stop_event.clear()

    source_dir = dpg.get_value("source_dir")
    destination_dir = dpg.get_value("destination_dir")
    conversion_mode = dpg.get_value("conversion_mode")
    compression_level = dpg.get_value("compression_level")
    num_threads = dpg.get_value("num_threads")
    log_enabled = dpg.get_value("log")

    log_file = None
    if log_enabled:
        log_file = os.path.join(os.path.dirname(__file__), "conversion_log.txt")
        log_message("Logging enabled. Log file: " + log_file, log_file)

    file_ext = "*.linear" if conversion_mode == "linear2mca" else "*.mca"
    file_list = glob(os.path.join(source_dir, file_ext))
    total_files = len(file_list)

    if total_files == 0:
        log_message("No files found to convert", log_file)
        return

    log_message(f"Found {total_files} region files to convert", log_file)
    log_message(f"Using {num_threads} processing threads", log_file)

    process_args = [
        (file, conversion_mode, destination_dir, compression_level, log_enabled, log_file)
        for file in file_list
    ]

    dpg.set_value("progress_bar", 0.0)
    dpg.set_value("progress_bar_text", f"Progress: 0.00%")

    with Manager() as manager:
        processed_files = manager.Value('i', 0)
        total_converted = manager.Value('i', 0)
        total_skipped = manager.Value('i', 0)

        def update_callback(result):
            converted, skipped, file = result

            total_converted.value += converted
            total_skipped.value += skipped
            processed_files.value += 1

            progress = processed_files.value / total_files
            percentage = progress * 100
            dpg.set_value("progress_bar", progress)
            dpg.set_value("progress_bar_text", f"Progress: {percentage:.2f}%")

            if log_enabled:
                status = "converted" if converted else "skipped"
                log_message(f"File {processed_files.value}/{total_files} {status}: {file}", log_file)

        with Pool(processes=num_threads) as pool:
            results = [pool.apply_async(process_file_wrapper, (arg,), callback=update_callback)
                       for arg in process_args]

            for r in results:
                r.wait()

            log_message(
                f"Conversion complete: {total_converted.value} region files converted, {total_skipped.value} region files skipped",
                log_file)

def stop_conversion_callback(sender, app_data, user_data):
    global stop_event
    stop_event.set()
    log_message("Conversion process stopped by user")

def validate_directory_path(sender, app_data, user_data):
    path = dpg.get_value(sender)
    if not os.path.isdir(path):
        dpg.set_value("log_text", f"Invalid directory path: {path}")

def on_resize(sender, app_data):
    new_width, new_height = dpg.get_viewport_client_width(), dpg.get_viewport_client_height()
    dpg.set_item_width("main_window", new_width)
    dpg.set_item_height("main_window", new_height)

dpg.create_context()

font_path = os.path.join(os.path.dirname(__file__), "font/DejaVuSans.ttf")

with dpg.font_registry():
    with dpg.font(font_path, 20) as default_font:
        dpg.add_font_range_hint(dpg.mvFontRangeHint_Cyrillic)

dpg.bind_font(default_font)

default_threads = cpu_count()

with dpg.window(label="Linear Region File Converter", width=800, height=600,
                no_title_bar=True, no_move=False, tag="main_window",
                no_resize=False, no_scrollbar=False):
    dpg.add_input_text(label="Source Directory", tag="source_dir", callback=validate_directory_path)
    dpg.add_button(label="Select Source Directory", callback=lambda: dpg.show_item("source_dir_dialog"))
    dpg.add_input_text(label="Destination Directory", tag="destination_dir", callback=validate_directory_path)
    dpg.add_button(label="Select Destination Directory", callback=lambda: dpg.show_item("destination_dir_dialog"))
    dpg.add_combo(label="Conversion Mode", items=["mca2linear", "linear2mca"], tag="conversion_mode", default_value="mca2linear")
    dpg.add_slider_int(label="Compression Level", default_value=6, min_value=1, max_value=22, tag="compression_level")
    dpg.add_slider_int(label="Number of Processing Threads", default_value=default_threads,
                       min_value=1, max_value=max(16, default_threads), tag="num_threads")
    dpg.add_checkbox(label="Log", tag="log")
    dpg.add_button(label="Convert Files", callback=convert_files_callback)
    dpg.add_button(label="Stop Conversion", callback=stop_conversion_callback)
    dpg.add_text("Progress Bar: ")
    dpg.add_progress_bar(label="Progress", tag="progress_bar", default_value=0.0)
    dpg.add_text("", tag="progress_bar_text")
    dpg.add_text("", tag="log_text")

with dpg.file_dialog(directory_selector=True, show=False, callback=select_source_directory_callback,
                     tag="source_dir_dialog"):
    dpg.add_file_extension(".*")

with dpg.file_dialog(directory_selector=True, show=False, callback=select_destination_directory_callback,
                     tag="destination_dir_dialog"):
    dpg.add_file_extension(".*")

dpg.create_viewport(title='Linear Region File Converter', width=800, height=600, resizable=True)
dpg.set_viewport_resize_callback(on_resize)

dpg.setup_dearpygui()
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()