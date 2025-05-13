Small example of a choice set generation and discrete choice experiment running on Streamlit (on Render). 

choicesets_GAMS.py is a file for generating the choice sets. 
test.py is the code running on Streamlit for the choice experiment: 
https://choiceexperiment.onrender.com 

The choicedesign package in Python has some bugs, so it might be necessary to include changes in the algorithm.py and design.py. These changes are listed in choicesets_GAMS.py as a comment at the beginning. 

File dynamic_figure_generation.py includes an example on how to dynamically set up a figure, based on the attribute values (in this case, D2D). 
