Title: A Camera-Based Virtual Keyboard System
Date: 2013-12-10
Category: Python
Slug: vkeyboard
Summary: A brief summary of my term project for ECE 532

In the Fall of 2013, I developed a camera-based keyboard system as my
term project for an image analysis course. This page provides a brief
summary of my project.

In my system, a webcam looks down on a user's hands, which rest on a
paper keyboard template. My program collects images from the webcam to
determine when and where the user touches the keyboard template. When
the user touches a key, my program produces the corresponding letter
as output.

Virtual keyboards are still actively researched in computer science
and electrical engineering. The system I implemented uses techniques
published in [1]-[3] between 2010 and 2013. Camera-based virtual
keyboards require a number of interesting image analysis techniques to
implement. They are particularly of interest in mobile applications
and in areas where one would like to avoid the cost of a physical
keyboard (for example, projects providing computers to people in the
developing world).

# Processing Steps

The virtual keyboard system I implemented needed to solve three main
problems:

1. Detect the locations of the user's fingertips.

2. Detect whether any fingertips are in contact with the tabletop.

3. When a fingertip touches the tabletop, determine which key was
pressed on the keyboard.

The first problem can be solved by segmenting an input image $I$ into
two regions: one representing the hands and another representing the
background. For each connected component of the hand region, we can
extract a contour $\gamma$ that traverses the boundary
counterclockwise. Places where $\gamma$ has high curvature (the
places where $\gamma$ bends the most sharply) typically correspond to
fingertips.

![Virtual keyboard processing steps.]({static}/images/vkeyboard/kb_processing.png)

I addressed the second problem using a technique called *shadow
analysis*, which is discussed in [1]. With this technique, we perform
another segmentation on $I$, to locate the regions in the image that
represent the shadows of the user's hands. Then, we examine small
neighborhoods near the user's fingertips. If the proportion of
shadow-pixels in a given neighborhood is above a certain threshold, we
infer that the corresponding fingertip is not in contact with the
tabletop (because it has a shadow). Otherwise, we declare that
fingertip to be touching the keyboard.

The last problem is solved by making some assumptions about the
geometry of the keyboard and imaging system. I assumed that the
keyboard template displays four easily identifiable control points
arranged in a rectangle, and that the front edge of the control
rectangle is parallel to the $x$-axis of the camera's coordinate
system. With these additional assumptions, it isn't too hard to invert
the perspective projection and recover the keyboard-space coordinates
of each keypress from the image-space coordinates of the fingertips.

# Results

After implementing my virtual keyboard system in python, I analyzed
its performance under different lighting and usage conditions. My
tests suggest that a camera-based user interface that uses shadow
analysis will work best under conditions where one has fine control
over the lighting conditions and the user does not need to enter very
much data at one time. For example, a camera-based user interface
would work well in an interactive museum exhibit, but it might not be
a very good tool for word processing in a dark coffee shop. Currently,
camera-based keyboards cannot provide the speed and accuracy
achievable on physical keyboards (but for that matter, neither do
touchscreen keyboards).

# Downloads

Below are links to the paper and code I wrote for the term project. I
used the code within [ipython](http://ipython.org/) to conduct my
experiments, and used the [OpenCV](http://opencv.org/) project to get
data from the camera. OpenCV's support for python is still under
development, so if you examine my code you may have to adapt it to
work with your particular hardware and copy of OpenCV.

* Paper:
  [A Camera Based Virtual Keyboard with Touch Detection by Shadow Analysis]({static}/docs/vkeyboard/vkeyboard.pdf)

* Project Code: [vkeyboard.zip]({static}/docs/vkeyboard/vkeyboard.zip)

References
----------

1. Y. Adajania, J. Gosalia, A. Kanade, H. Mehta, and N. Shekokar. Virtual
keyboard using shadow analysis. In Emerging Trends in Engineering and
Technology (ICETET), 2010 3rd International Conference on, page 163 to
165, 2010.

2. E. Posner, N. Starzicki, and E. Katz. A single camera based floating virtual
keyboard with improved touch detection. In Electrical Electronics Engineers
in Israel (IEEEI), 2012 IEEE 27th Convention of, page 1 to 5, 2012.

3. M. Hagara and J. Pucik. Fingertip detection for virtual keyboard
based on camera. In Radioelektronika (RADIOELEKTRONIKA), 2013 23rd
International Conference, page 356 to 360, 2013.
