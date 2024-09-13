from PySide6 import QtCore

def loadQssFile(file_path):
    """Loads the contents of a styles.qcc file into a string variable.

    Args:
        file_path (str): The path to the styles.qcc file.

    Returns:
        str: The contents of the styles.qcc file as a string.
    """

    try:
        file = QtCore.QFile(file_path)

        if not file.open(QtCore.QIODevice.ReadOnly | QtCore.QIODevice.Text):
            raise IOError("Failed to open styles.qcc file: " + file.errorString())

        data = file.readAll().data()
        file.close()

        return data.decode("utf-8")
    except Exception as e:
        print("Error loading styles.qcc file:", str(e))
        return None
