import pygame as pg
import numpy as np
import math
from pygame import gfxdraw
from random import randint
from perlin_noise import PerlinNoise
from numba import njit

# Debug tools
GRAB_MOUSE = True  # Hide the mouse and lock it to the centre of the window
PROFILE = True # Activate the profiler
WIREFRAME = False # Render a wireframe instead of the filled faces
INSERTION_SORT = False

# The width and height of the window the game is displayed on
WIDTH, HEIGHT = 1920, 1080
WIDTH, HEIGHT =  1000, 1000
CENTRE = (WIDTH//2, HEIGHT//2)
ASPECT_RATIO = WIDTH / HEIGHT

# Rendering
BACKGROUND_COLOR = (32, 32, 32)
WIREFRAME_COLOR = (0, 127, 0)

# The maximum number of times the main loop can run per second
MAX_FPS = 60    


# The size, area and volume of a single chunk
CHUNK_SIZE = 16
CHUNK_AREA = CHUNK_SIZE**2
CHUNK_VOLUME = CHUNK_SIZE**3

# World Generation
OCTAVES = 2
SEED = 10247
NOISE = PerlinNoise(octaves=OCTAVES, seed=SEED)


# Player variables
PLAYER_SPEED = 5  # Voxels per second
PLAYER_ROTATION_SENSITIVITY = 15
VERTICAL_FOV = 1  # (Radians)
RENDER_DISTANCE = 3

# Clipping planes
NEAR = 0.1
FAR = 10000



def clamp(n, minn, maxn):
    return max(minn, min(n, maxn))


VERTICES = [
    pg.Vector3((-0.5, -0.5, -0.5)),
    pg.Vector3((0.5, -0.5, -0.5)),
    pg.Vector3((0.5, 0.5, -0.5)),
    pg.Vector3((-0.5, 0.5, -0.5)),
    pg.Vector3((-0.5, -0.5, 0.5)),
    pg.Vector3((0.5, -0.5, 0.5)),
    pg.Vector3((0.5, 0.5, 0.5)),
    pg.Vector3((-0.5, 0.5, 0.5)),
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
    pg.Vector3((0, 0, -1)),
    pg.Vector3((0, 0, 1)),
    pg.Vector3((-1, 0, 0)),
    pg.Vector3((1, 0, 0)),
    pg.Vector3((0, -1, 0)),
    pg.Vector3((0, 1, 0)),
]

voxel_types = [
    (0, 127, 127),
    (127, 0, 127),
    (127, 127, 0),
    (127, 127, 127),
]
