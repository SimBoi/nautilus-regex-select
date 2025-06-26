from typing import List
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import GObject, Adw, Gtk, Nautilus


# shows an alert dialog with a heading and body text to the user
def message_alert(heading: str, body: str, dismiss_label: str = 'Dismiss', parent: Adw.Dialog = None):
    dialog = Adw.AlertDialog(
            heading=heading,
            body=body,
        )
    dialog.add_response(
            id=dismiss_label,
            label=dismiss_label,
        )
    dialog.present(parent)

# get all files in the specified directory and its subdirectories
def get_all_files(directory: str, search_subdirectories: bool, max_files: int, max_file_size: int, parent: Adw.Dialog) -> List[str]:
    import os
    try:
        file_paths = []
        for root, _, files in os.walk(directory):
            for file in files:
                # skip files that are too large
                file_path = os.path.join(root, file)
                if os.path.getsize(file_path) > max_file_size:
                    continue

                # append the full path of the file
                file_paths.append(os.path.join(root, file))
                if len(file_paths) >= max_files:
                    message_alert(
                        heading="File Limit Reached",
                        body=f"Will only process the first {max_files} files found.",
                        parent=parent,
                    )
                    return file_paths
            if not search_subdirectories:
                break
        return file_paths
    except Exception as e:
        message_alert(
            heading="File Retrieval Error",
            body=f"Failed to retrieve files: {e}",
            parent=parent,
        )
        return

# returns a list of file paths for files that contain a match for the given regex in their names
def regex_match_names(file_paths: List[str], regex: str, parent: Adw.Dialog) -> List[str]:
    if not regex:
        return file_paths  # No filtering if no regex is specified
    import re, os
    try:
        pattern = re.compile(regex)
    except re.error as e:
        message_alert(
            heading="Invalid Regex",
            body=f"Your filename regex is invalid:\n{e}",
            parent=parent,
        )
        return

    matches = []
    file_paths = [str(os.path.basename(file_path)) for file_path in file_paths]  # only check the file names, not the full paths
    for file_path in file_paths:
        if pattern.search(file_path):
            matches.append(file_path)
    return matches

# returns a list of file paths for files that contain a match for the given regex in their contents
def regex_match_contents(file_paths: List[str], regex: str, parent: Adw.Dialog) -> List[str]:
    if not regex:
        return file_paths  # No filtering if no regex is specified
    import re
    try:
        pattern = re.compile(regex)
    except re.error as e:
        message_alert(
            heading="Invalid Regex",
            body=f"Your content regex is invalid:\n{e}",
            parent=parent,
        )
        return

    # Use charset_normalizer to read file contents with auto-detection of encoding
    matches = []
    from charset_normalizer import from_path
    for file_path in file_paths:
        try:
            content = from_path(file_path).best()
            if content and pattern.search(str(content)):
                matches.append(file_path)
        except Exception as e:
            pass  # Ignore files that cannot be read or processed
    return matches

# opens the files in the default application for their file type
def open_files(file_paths: List[str], working_dir: str, parentDialog: Adw.Dialog):
    import subprocess
    try:
        for file_path in file_paths:
            subprocess.run(['xdg-open', file_path], check=True, cwd=working_dir)
        parentDialog.close()
    except subprocess.CalledProcessError as e:
        message_alert(
            heading="Open Files Error",
            body=f"Failed to open files: {e}",
            parent=parentDialog,
        )

# moves the files to the specified destination directory
def move_files(file_paths: List[str], destination_directory: str, working_dir: str, parentDialog: Adw.Dialog):
    if not destination_directory:
        message_alert(
            heading="Move Files Error",
            body="Destination directory is not specified.",
            parent=parentDialog,
        )
        return

    import subprocess
    try:
        subprocess.run(['mkdir', '-p', destination_directory], check=True, cwd=working_dir)
        for file_path in file_paths:
            subprocess.run(['mv', file_path, destination_directory], check=True, cwd=working_dir)
        # subprocess.run(["nautilus", destination_directory], check=True, cwd=working_dir)  # TODO figure out why this is not working
        parentDialog.close()
    except subprocess.CalledProcessError as e:
        message_alert(
            heading="Move Files Error",
            body=f"Failed to move files: {e}",
            parent=parentDialog,
        )

# copies the files to the specified destination directory
def copy_files(file_paths: List[str], destination_directory: str, working_dir: str, parentDialog: Adw.Dialog):
    if not destination_directory:
        message_alert(
            heading="Copy Files Error",
            body="Destination directory is not specified.",
            parent=parentDialog,
        )
        return

    import subprocess
    try:
        subprocess.run(['mkdir', '-p', destination_directory], check=True, cwd=working_dir)
        for file_path in file_paths:
            subprocess.run(['cp', file_path, destination_directory], check=True, cwd=working_dir)
        # subprocess.run(["xdg-open", destination_directory], check=True, cwd=working_dir)  # TODO figure out why this is not working
        parentDialog.close()
    except subprocess.CalledProcessError as e:
        message_alert(
            heading="Copy Files Error",
            body=f"Failed to copy files: {e}",
            parent=parentDialog,
        )

# deletes the specified files
def delete_files(file_paths: List[str], working_dir: str, parentDialog: Adw.Dialog):
    import subprocess
    try:
        for file_path in file_paths:
            subprocess.run(["rm", "-f", file_path], check=True, cwd=working_dir)
        parentDialog.close()
    except subprocess.CalledProcessError as e:
        message_alert(
            heading="Delete Files Error",
            body=f"Failed to delete files: {e}",
            parent=parentDialog,
        )


class RegexSelectDialog(Adw.Dialog):
    def __init__(self, folder: Nautilus.FileInfo):
        super().__init__()

        self.working_dir = folder.get_location().get_path()

        # Set up the dialog properties
        self.set_title('Regex Select')
        self.set_content_width(450)
        root = Adw.ToolbarView()
        header_bar = Adw.HeaderBar()
        header_bar.set_decoration_layout(':close')
        root.add_top_bar (header_bar)
        body = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            hexpand=True,
            spacing=8,
            margin_top=16,
            margin_bottom=16,
            margin_start=16,
            margin_end=16,
        )
        root.set_content(body)
        list_box = Gtk.ListBox(css_classes=['boxed-list-separate'])
        body.append(list_box)

        # Create the entry for the regex patterns and destination directory
        self.name_regex_entry = Adw.EntryRow(title='filename regex (Empty=no-filter)')
        list_box.append(self.name_regex_entry)
        self.content_regex_entry = Adw.EntryRow(title='content regex (Empty=no-filter)')
        list_box.append(self.content_regex_entry)
        self.destination_directory_entry = Adw.EntryRow(title='Destination Directory (for move/copy actions)')
        list_box.append(self.destination_directory_entry)

        # entry for max number of files to process and max file size
        self.max_files_entry = Adw.EntryRow(title='Max Files to Process (Empty=no-limit)')
        list_box.append(self.max_files_entry)
        self.max_file_size_entry = Adw.EntryRow(title='Max File Size (in bytes, Empty=no-limit)')
        list_box.append(self.max_file_size_entry)

        # checkbox to search in subdirectories
        self.search_subdirectories_checkbox = Gtk.CheckButton(
            label='Search in subdirectories',
            css_classes=['pill'],
            halign=Gtk.Align.START,
            margin_top=8,
        )
        body.append(self.search_subdirectories_checkbox)

        # Create the list box for the actions delete(in red), copy, move, and open actions
        action_list = Gtk.ListBox(css_classes=["boxed-list"])
        action_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        action_list.set_activate_on_single_click(True)
        # when a row is activated (single-click), call our handler
        action_list.connect(
            "row-activated",
            lambda listbox, row: self.select_action(row.get_child().get_label()),
        )
        body.append(action_list)
        actions = ['Delete', 'Copy', 'Move', 'Open']
        for action in actions:
            row = Gtk.ListBoxRow()
            label = Gtk.Label(
                label=action,
                css_classes=["list-item"],
                margin_top=4,
                margin_bottom=4,
            )
            row.set_child(label)
            action_list.append(row)
        self.selected_action = None

        # Create the Start Search button
        self.submit_button = Gtk.Button(
            label='Start Search',
            css_classes=['pill', 'suggested-action'],
            halign=Gtk.Align.CENTER,
            margin_top=8,
        )
        body.append(self.submit_button)
        self.submit_button.connect(
            'clicked',
            lambda *_: self.start_search(),
            None,
        )

        self.set_child(root)

    def select_action(self, action: str):
        self.selected_action = action

    def start_search(self):
        if not self.selected_action:
            message_alert(
                heading="Action Not Selected",
                body="Please select an action (Open, Move, Copy, Delete) before proceeding.",
                parent=self,
            )
            return

        file_paths = get_all_files(
            directory=self.working_dir,
            search_subdirectories=self.search_subdirectories_checkbox.get_active(),
            max_files=int(self.max_files_entry.get_text() if self.max_files_entry.get_text() else 2**31-1),  # Default to max int if no input
            max_file_size=int(self.max_file_size_entry.get_text() if self.max_file_size_entry.get_text() else 2**31-1),  # Default to max int if no input
            parent=self,
        )
        if file_paths is None: return
        file_paths = regex_match_names(
            file_paths=file_paths,
            regex=self.name_regex_entry.get_text(),
            parent=self,
        )
        if file_paths is None: return
        file_paths = regex_match_contents(
            file_paths=file_paths,
            regex=self.content_regex_entry.get_text(),
            parent=self,
        )
        if file_paths is None: return

        if self.selected_action == 'Open':
            open_files(
                file_paths=file_paths,
                working_dir=self.working_dir,
                parentDialog=self,
            )
        elif self.selected_action == 'Move':
            move_files(
                file_paths=file_paths,
                destination_directory=self.destination_directory_entry.get_text(),
                working_dir=self.working_dir,
                parentDialog=self,
            )
        elif self.selected_action == 'Copy':
            copy_files(
                file_paths=file_paths,
                destination_directory=self.destination_directory_entry.get_text(),
                working_dir=self.working_dir,
                parentDialog=self,
            )
        elif self.selected_action == 'Delete':
            delete_files(
                file_paths=file_paths,
                working_dir=self.working_dir,
                parentDialog=self,
            )


class RegexSelectProvider(GObject.GObject, Nautilus.MenuProvider):
    def get_background_items(self, folder: Nautilus.FileInfo):
        menu_item = Nautilus.MenuItem(
            name="RegexSelectProvider::RegexSelect",
            label="Regex Select",
        )
        menu_item.connect(
            "activate",
            lambda *_: RegexSelectDialog(folder).present(None),
        )
        return [menu_item]
