import os
import csv
import glob
import sqlite3
from simple_term_menu import TerminalMenu

def get_annotation_db_path():
    """
    Returns the path to the Apple Books annotation database.

    This function searches for the AEAnnotation SQLite database in the default
    Apple Books container directory on macOS.

    Returns:
        str: The full path to the AEAnnotation SQLite database.
    """
    pattern = os.path.expanduser("~/Library/Containers/com.apple.iBooksX/Data/Documents/AEAnnotation/AEAnnotation*.sqlite")
    return glob.glob(pattern)[0]

def get_library_db_path():
    """
    Returns the path to the Apple Books library database.

    This function searches for the BKLibrary SQLite database in the default
    Apple Books container directory on macOS.

    Returns:
        str: The full path to the BKLibrary SQLite database.
    """
    pattern = os.path.expanduser("~/Library/Containers/com.apple.iBooksX/Data/Documents/BKLibrary/BKLibrary*.sqlite")
    return glob.glob(pattern)[0]

def get_library_books():
    """
    Retrieves all books from the local Apple Books library.

    This function connects to the BKLibrary database and fetches the asset ID,
    title, and author for all books in the library.

    Returns:
        dict: A dictionary where keys are asset IDs and values are tuples
              containing the book title and author. Unknown titles or authors
              are replaced with "Unknown Title" or "Unknown Author" respectively.
    """
    with sqlite3.connect(get_library_db_path()) as conn:
        cursor = conn.cursor()
        cursor.execute(f'''SELECT ZASSETID, ZSORTTITLE, ZSORTAUTHOR
                           FROM ZBKLIBRARYASSET''')
        return {row[0]: (row[1] or "Unknown Title", row[2] or "Unknown Author") for row in cursor.fetchall()}

def get_library_books_with_highlights():
    """
    Retrieves asset IDs of books in the local Apple Books library that have 
    highlights or annotations.

    This function first gets all book asset IDs from the library, then queries
    the annotation database to find which of these books have non-empty
    annotations.

    Returns:
        list: A list of asset IDs for books that have highlights or annotations.
    """
    book_ids = list(get_library_books().keys())
    placeholders = ','.join('?' for _ in book_ids)
    with sqlite3.connect(get_annotation_db_path()) as conn:
        cursor = conn.cursor()
        cursor.execute(f'''SELECT DISTINCT ZANNOTATIONASSETID 
                          FROM ZAEANNOTATION 
                          WHERE ZANNOTATIONASSETID IN ({placeholders}) 
                          AND ZANNOTATIONSELECTEDTEXT != "";''', book_ids)
        return [entry[0] for entry in cursor.fetchall()]
    
def export_annotations(asset_id: str, format: str):
    """
    Export annotations (highlights and notes) for a specific book to a file.

    This function retrieves all non-empty annotations for a given book from the
    Apple Books annotation database and writes them to a file in the specified format.

    Args:
        asset_id (str): The unique identifier for the book in the Apple Books library.
        format (str): The desired output format ('csv' or 'markdown').

    Returns:
        str: The name of the file where annotations were exported.
    """
    with sqlite3.connect(get_annotation_db_path()) as conn:
        cursor = conn.cursor()
        cursor.execute(f'''SELECT ZANNOTATIONSELECTEDTEXT, ZANNOTATIONNOTE
                          FROM ZAEANNOTATION
                          WHERE ZANNOTATIONASSETID = ? AND ZANNOTATIONSELECTEDTEXT != "";''', (asset_id,))
        annotations = cursor.fetchall()

    if format.lower() not in ['csv', 'markdown']:
        raise ValueError("Unsupported format! Please use 'csv' or 'markdown'!")

    if format.lower() == 'csv':
        filename = "highlights.csv"
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=["Highlight", "Notes"], delimiter=";")
            writer.writeheader()

            batch = []
            for (highlight, note) in annotations:
                batch.append({
                    "Highlight": highlight.replace("\n", " "),
                    "Notes": note.replace("\n", " ") if note else ""
                })
                
            writer.writerows(batch)

    elif format.lower() == 'markdown':
        filename = "highlights.md"
        with open(filename, 'w') as mdfile:
            for (highlight, note) in annotations:
                mdfile.write(f"{highlight}\n")
                if note:
                    mdfile.write(f"*{note}*\n")
                mdfile.write("---\n")

    return filename

def main():
    book_details = get_library_books()

    books = get_library_books_with_highlights()
    formats = ['csv', 'markdown']

    selected_book = None
    selected_format = formats[0]

    def get_main_menu_items():
        return [
            f"Select Book (Current: {book_details[selected_book][0] if selected_book else 'None'})",
            f"Select Format (Current: {selected_format if selected_format else 'None'})",
            "Export Annotations",
            "Quit"
        ]

    main_menu_title = "Apple Books Highlight Exporter"

    book_menu = TerminalMenu(
        [book_details[book][0] for book in books],
        title="Select a Book",
        menu_cursor=">> ",
        menu_cursor_style=("fg_red", "bold"),
        menu_highlight_style=("bg_red", "fg_black"),
    )

    format_menu = TerminalMenu(
        formats,
        title="Select Output Format",
        menu_cursor=">> ",
        menu_cursor_style=("fg_red", "bold"),
        menu_highlight_style=("bg_red", "fg_black"),
    )

    while True:
        main_menu = TerminalMenu(
            get_main_menu_items(),
            title=main_menu_title,
            menu_cursor=">> ",
            menu_cursor_style=("fg_red", "bold"),
            menu_highlight_style=("bg_red", "fg_black"),
        )
        
        main_choice = main_menu.show()

        if main_choice == 0:  # Select Book
            book_choice = book_menu.show()
            if book_choice is not None:
                selected_book = books[book_choice]
        elif main_choice == 1:  # Select Format
            format_choice = format_menu.show()
            if format_choice is not None:
                selected_format = formats[format_choice]
        elif main_choice == 2:  # Export Annotations
            if selected_book and selected_format:
                filename = export_annotations(selected_book, selected_format)
                print(f"Annotations exported to {filename}")
                break
            else:
                print("Please select a book and format before exporting!")
        elif main_choice == 3 or main_choice is None:  # Quit
            break

if __name__ == "__main__":
    main()