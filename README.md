# SmartTagger
SmartTagger is a tool that leverages the Segment Anything Model (SAM) to assist in automatically generating instance segmentation labels. 
Provides a graphical interface to facilitate label processing for non-computer professionals. The main function is to make it easier to create instance segmentation label data, along with some basic label drawing features.
It is written in Python and uses Pyside6 for its graphical interface.

## Set up the environment
You need install [Anaconda](https://www.continuum.io/downloads), then run below:
```
conda create --name=st python=3.10
conda activate st
# You can replace "st" with your environment name.
```
Pip install the ultralytics package including all [requirements](https://github.com/ultralytics/ultralytics/blob/main/pyproject.toml) in a [**Python>=3.8**](https://www.python.org/) environment with [**PyTorch>=1.8**](https://pytorch.org/get-started/locally/).
```
pip3 install torch torchvision torchaudio
pip install ultralytics
pip install shapely pyside6
```
Then navigate to the downloaded directory.
```
cd path/to/SmartTagger
python main.py
```
![Main_window](https://github.com/user-attachments/assets/056a8fff-9062-409c-b9f4-0c27d666f3d6)



## How to Use

If you already have some labels, please store them in the following format. The 'classes.txt' corresponds to the category names. There are three types of labels to be placed in the folder, all in YOLO format by default.

```none
Project Directory Structure:
- /labels
  - classes.txt
  - Box/
    - file1.txt
  - Point/
    - file1.txt
  - Polygon/
    - file1.txt

```
***
First, you need to load images and labels. You can load a single image or select an image folder using the buttons below. Then, load the label folder according to the format mentioned above.
![load](https://github.com/user-attachments/assets/64bd9afa-654e-47db-af2b-c230406a2a52)

***
You can use any YOLO model to generate box labels. Select the model and the current image, then press the button. On the left, you can select the model and set the confidence level. This confidence applies to both YOLO and SAM, depending on which button you press.
***

### If you want to add normal labels, you can do so directly. If you want to use SAM, there are two methods:

1.  Add SAM labels (in point and box forms).
    
2.  Pass the current points or boxes to SAM for segmentation. Stay in the label list you want to use, select the labels you want to pass, and then click 'Perform SAM Segmentation.'
    

Remember to save. All shortcuts are in parentheses.
I hope this project helps improve your work efficiency.
