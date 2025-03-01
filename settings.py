import pygame as pg
import numpy as np
import math
from perlin_noise import PerlinNoise
from numba import njit, prange
from random import randint

# Debug tools
GRAB_MOUSE = True  # Hide the mouse and lock it to the centre of the window
WIREFRAME = False # Render a wireframe instead of the filled faces
INSERTION_SORT = False

# Window
WIDTH, HEIGHT =  1080, 1080
CENTRE = (WIDTH//2, HEIGHT//2)
ASPECT_RATIO = WIDTH / HEIGHT
MAX_FPS = 120    

# World TODO refactor into database
SKY_COLOR = (135, 206, 235)
WIREFRAME_COLOR = (0, 127, 0)

# The size, area and volume of a single chunk
CHUNK_SIZE = 16
CHUNK_AREA = CHUNK_SIZE**2
CHUNK_VOLUME = CHUNK_SIZE**3

# Player variables
PLAYER_SPEED = 5  # Voxels per second
PLAYER_ROTATION_SENSITIVITY = 15
VERTICAL_FOV = 1  # (Radians)
RENDER_DISTANCE = 4

# Clipping plane(s)
NEAR = 0.1


VERTICES = [
    (-0.5, -0.5, -0.5),
    (0.5, -0.5, -0.5),
    (0.5, 0.5, -0.5),
    (-0.5, 0.5, -0.5),
    (-0.5, -0.5, 0.5),
    (0.5, -0.5, 0.5),
    (0.5, 0.5, 0.5),
    (-0.5, 0.5, 0.5),
]

FACES = [
    (0, 1, 2, 3),  # Front face
    (4, 5, 6, 7),  # Back face
    (4, 0, 3, 7),  # Left face
    (1, 5, 6, 2),  # Right face
    (4, 5, 1, 0),  # Top face
    (3, 2, 6, 7),  # Bottom face
]

FACE_NORMALS = [
    (0, 0, -1),
    (0, 0, 1),
    (-1, 0, 0),
    (1, 0, 0),
    (0, -1, 0),
    (0, 1, 0),
]

voxel_types = [
    (127, 16, 70),
    (127, 108, 0),
    (16, 88, 127),
    (127, 127, 127),
]


def clamp(n, minn, maxn):
    return max(minn, min(n, maxn))



def toFlat(position):
    """
    This function is used when converting from local chunk positions to indices to access data in the chunk array
    """
    # Convert a 3d position to a 1d index
    index = position[0] + (position[1] * CHUNK_SIZE) + (position[2] * CHUNK_AREA)
    return int(index)

def to3d(index):
    """
    This function converts from an index in the chunk array to a 3d position in the chunk
    """

    # Convert a 1d index to a 3d position
    index = int(index[0])  # index[0] because index is a numpy array, so it shouldnt be directly used

    z = int(index / CHUNK_AREA)
    index -= z * CHUNK_AREA

    y = int(index / CHUNK_SIZE)

    x = int(index % CHUNK_SIZE)     

    return (x, y, z)   
