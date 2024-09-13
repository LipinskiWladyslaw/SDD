# Adding images
1. Add images to `/img` folder
2. add `<file>[imagepath]</file>` to `widget_images.qrc`
3. run `pyside6-rcc widget_images.qrc -o widget_images.py`
4. specify image path as `:/[imagepath]` in `.py` and `.qss` files
