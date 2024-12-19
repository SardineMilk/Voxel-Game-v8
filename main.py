from settings import *

if PROFILE:
    import profiler
    profiler.profiler(sortby="tottime").start(True)


class Camera:
    def __init__(self, starting_position: pg.Vector3, starting_rotation: pg.Vector3):
        self.position = pg.Vector3(starting_position)
        self.rotation = pg.Vector3(starting_rotation)
    
    def move(self, keys, delta: int):
        speed = PLAYER_SPEED / (delta*1000)
        yaw = math.radians(self.rotation.x)

        if keys[pg.K_w]:  # Move forward
            self.position.x += math.sin(yaw) * speed
            self.position.z += math.cos(yaw) * speed
        if keys[pg.K_s]:  # Move backward
            self.position.x -= math.sin(yaw) * speed
            self.position.z -= math.cos(yaw) * speed
        if keys[pg.K_d]:  # Strafe left
            self.position.x += math.cos(yaw) * speed
            self.position.z -= math.sin(yaw) * speed
        if keys[pg.K_a]:  # Strafe right
            self.position.x -= math.cos(yaw) * speed
            self.position.z += math.sin(yaw) * speed
        if keys[pg.K_SPACE]:  # Move up
            self.position.y -= speed
        if keys[pg.K_LSHIFT]:  # Move down
            self.position.y += speed

    def rotate(self, mouse_movement: tuple[int, int], delta:int):
        yaw   = mouse_movement[0] * PLAYER_ROTATION_SENSITIVITY * (delta / 1000)
        pitch = mouse_movement[1] * PLAYER_ROTATION_SENSITIVITY * (delta / 1000)

        rotation_vector = pg.Vector3((yaw, pitch, 0))
        # Add the rotation vector to the player rotation 
        self.rotation = self.rotation + rotation_vector
        # Clamp the pitch to directly up/down
        self.rotation.y = clamp(self.rotation.y, -90, 90)
    

class World:
    def __init__(self):
        self.chunks = []
        self.changed = True  # If any chunk meshes have changed, we set this to tre

    def getVoxel(self, position):
        chunk_position, local_position = self.__worldToLocal(position)
        chunk = self.__getChunk(chunk_position)
        voxel = chunk.getVoxel(local_position)
        return voxel

    def setVoxel(self, position, type):
        chunk_position, local_position = self.__worldToLocal(position)
        chunk = self.__getChunk(chunk_position)
        chunk.setVoxel(local_position, type)

    def update(self, camera):
        self.updateRenderedChunks(camera.position)
        if self.changed:
            self.constructMesh()

    def updateRenderedChunks(self, player_pos):
        chunks_to_load = []
        # Builds a list of chunks that need to be loaded
        for i in range(RENDER_DISTANCE ** 3):
            # Generate an [x, y, z] index in a cube pattern
            x = i % RENDER_DISTANCE
            y = (i // RENDER_DISTANCE) % RENDER_DISTANCE
            z = i // RENDER_DISTANCE ** 2

            # Shift so chunks generate centred on the player
            x = int((player_pos.x//CHUNK_SIZE) + x) - RENDER_DISTANCE//2
            y = int((player_pos.y//CHUNK_SIZE) + y) - RENDER_DISTANCE//2
            z = int((player_pos.z//CHUNK_SIZE) + z) - RENDER_DISTANCE//2

            loaded_chunk_position = (x, y, z)
            chunks_to_load.append(loaded_chunk_position)

        # Unload uneeded chunkss
        for chunk in self.chunks:
            if chunk.position not in chunks_to_load:
                # If chunk is not inside the player's render distance, we unload it
                self.changed = True
                self.chunks.remove(chunk)
        
        for chunk_position in chunks_to_load:
            if self.__getChunkIndex(list(chunk_position)) == None:
                # If the chunk is not loaded, we load it
                self.changed = True
                self.__loadChunk(chunk_position)

    def constructMesh(self):
        mesh = []
        for chunk in self.chunks:
            mesh += chunk.mesh
        self.mesh = np.array(mesh, dtype=Face)
    
    def __getChunk(self, position:tuple[int, int, int]):
        # If the chunk doesn't exist, load it
        chunk_index = self.__getChunkIndex(position)
        if chunk_index == None:
            self.__loadChunk(position)
            # loadChunk appends the chunk to the end of self.chunks
            # So it will be the last item in the list
            return self.chunks[-1]

        return self.chunks[chunk_index]

    def __getChunkIndex(self, position):
        # From a chunk position, get the 
        # Index of the chunk in the array of loaded chunks
        for index, chunk in enumerate(self.chunks):
            if chunk.position == tuple(position): 
                return index
        return None

    def __worldToLocal(self, position):
        # Convert a world position to a local position
        # Position of the chunk in 3d space
        chunk_index = [position[0] // CHUNK_SIZE, position[1] // CHUNK_SIZE, position[2] // CHUNK_SIZE]
        # Index of the voxel within the chunk
        local_index = [position[0] % CHUNK_SIZE, position[1] % CHUNK_SIZE, position[2] % CHUNK_SIZE]

        return tuple(chunk_index), tuple(local_index)

    def __loadChunk(self, position):
        # TODO - file opening
        self.chunks.append(Chunk(position))


class Chunk:
    def __init__(self, position):
        # Index of the chunk in 3d space - Tuple
        self.position = tuple(position)
        # Types of the voxels contained in the chunk - A flattened 1d numpy array of integers
        # It is stored this way for efficieny 
        self.voxels = self.__getChunkData()
        self.constructMesh()
    
    def getVoxel(self, position):
        """
        Fetch the voxel data at an (x, y, z) position in the chunk
        """
        x, y, z = position
        # Range check - If it's outside the chunk, we return 0
        if ((0 <= x < CHUNK_SIZE) and
            (0 <= y < CHUNK_SIZE) and
            (0 <= z < CHUNK_SIZE)):

            index = self.__ToFlat(position)
            return self.voxels[index]

        return 0   
    
    def setVoxel(self, position, type):
        """
        Set the voxel data at an (x, y, z) position in the chunk
        Then rebuild the chunk mesh
        """

        x, y, z = position
        # Range check - Is it inside the chunk?
        if (0 <= x <= CHUNK_SIZE - 1 or 
            0 <= y <= CHUNK_SIZE - 1 or
            0 <= z <= CHUNK_SIZE - 1):
                index = self.__ToFlat(position)
                self.voxels[index] = type
                self.constructMesh()

    def constructMesh(self):
        """
        This constructs the chunk mesh
        It takes the form of a list, with each element being a Face object

        The face_index determines which side of the voxel the face belongs to, with the lookup table stored in settings.py
        TODO move from settings.py (voxel.py?)

        The voxel_type is technically uneeded, as world.getVoxel(voxel_world_pos) can be called to get the type
        However, it gives a massive performance boost
        """

        chunk_offset = pg.Vector3(self.position)*CHUNK_SIZE

        self.mesh = []
        filtered_voxels = np.argwhere(self.voxels != 0)
        for voxel_index in filtered_voxels:
            voxel_pos = pg.Vector3(self.__To3d(voxel_index))

            for face_index, face_normal in enumerate(FACE_NORMALS):
                # Interior Face Culling
                check_pos = voxel_pos + face_normal
                neighbour_type = self.getVoxel(check_pos)
                if neighbour_type == 0:

                    voxel_world_pos = tuple((chunk_offset + pg.Vector3(voxel_pos)))

                    voxel_type = self.getVoxel(voxel_pos)

                    self.mesh.append(Face(voxel_world_pos, face_index, voxel_type))

    def __ToFlat(self, position):
        """
        This function is used when converting from local chunk positions to indices to access data in the chunk array
        """
        # Convert a 3d position to a 1d index
        index = position[0] + (position[1] * CHUNK_SIZE) + (position[2] * CHUNK_AREA)
        return int(index)
    
    def __To3d(self, index):
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

    def __getChunkData(self):
        """
        Get the voxel data for this chunk
        Either from the file or the terrain generator
        """
        already_generated = False
        if already_generated:
            # Load From File
            pass
        else:
            return self.__generateTerrain()

    def __generateTerrain(self):
        """
        Procedurally generate the chunk terrain
        """

        voxels = np.zeros(CHUNK_VOLUME, dtype=int)
        for i in range(CHUNK_SIZE):
            for j in range(CHUNK_SIZE):
                if self.position[1] == 0:
                    voxel_type = (math.sqrt(((i+self.position[0]*CHUNK_SIZE)**2)%80+
                                            ((j+self.position[2]*CHUNK_SIZE)**2)%80)//2
                                ) %3+1
                    index = self.__ToFlat((i, 0, j))

                    voxels[index] = voxel_type
        return voxels


class Renderer:
    """
    This class's purpose is to take in the mesh and render the faces to the screen.
    This involves:
        - Sorting the mesh
        - Culling the mesh
            - Backface culling
            - Frustum culling
        - Processing the mesh
            - Translating
            - Rotating
            - Projecting
        - Drawing the mesh

    """
    def __init__(self, surface):
        # The surface the renderer will draw on
        self.surface = surface

        # Vectorise the drawFace function
        self.drawMesh = np.vectorize(self.__drawFace)
    
    def render(self, mesh):
        """
        Process the mesh, then draw it on the screen
        """
        if len(mesh) == 0:
            return
        
        processed_mesh = processMesh(mesh, tuple(camera.position), tuple(camera.rotation))

        if len(processed_mesh) == 0:
            return
            
        sorted_mesh = sorted(processed_mesh, key=lambda x: x[2])[::-1]

        for face in sorted_mesh:
            pg.draw.polygon(self.surface, face[1], face[0], width=WIREFRAME)

    def __drawFace(self, face):
        points, color = face
        pg.draw.polygon(self.surface, color, points, width=WIREFRAME)


def processMesh(mesh, camera_position, camera_rotation):
    # Using the mesh, return a list of faces that must be drawn
    processed_mesh = []  # (Points, Colour, Depth)
    sin_yaw =   math.sin(math.radians(-camera_rotation[0]))
    cos_yaw =   math.cos(math.radians(-camera_rotation[0]))
    sin_pitch = math.sin(math.radians(camera_rotation[1]))
    cos_pitch = math.cos(math.radians(camera_rotation[1]))
    
    for face in mesh:
        processed_face = processFace(face.position, face.index, sin_yaw, cos_yaw, sin_pitch, cos_pitch, camera_position)
        if processed_face != None:
            if processed_face[0] != None:
                points, depth = processed_face
                processed_mesh.append((points, face.colour, depth))
    return processed_mesh

    
@njit
def processFace(voxel_position, face_index, sin_yaw, cos_yaw, sin_pitch, cos_pitch, camera_position):
        """
        - Translate face
        If face is visible:
            - Rotate
            - Project
            - Return processed_face
        """
        #TODO pass these as parameters
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
        relative_voxel_position = (
                                    voxel_position[0] - camera_position[0],
                                    voxel_position[1] - camera_position[1],
                                    voxel_position[2] - camera_position[2]
                                )  # Relative to the camera - (0, 0, 0) is the camera position

        # This performs backface culling
        normal = FACE_NORMALS[face_index]
        face_to_camera = (
                            relative_voxel_position[0] * normal[0] +
                            relative_voxel_position[1] * normal[1] +
                            relative_voxel_position[2] * normal[2] 
                        )
        is_visible =  (face_to_camera <= -0.5)
        
        # If it's culled, skip the rest of the function
        if not is_visible:
            return None

        # processed_face will always have length 4, so .append() is not needed
        processed_face = []

        inside = False

        for i, vertex_index in enumerate(FACES[face_index]):
            model_vertex_position = VERTICES[vertex_index]  # Indexes into the VERTICES array
            
            vertex = (
                        relative_voxel_position[0] + model_vertex_position[0],
                        relative_voxel_position[1] + model_vertex_position[1],
                        relative_voxel_position[2] + model_vertex_position[2]
                    ) 

            x, y, z = vertex
            x, z = x * cos_yaw + z * sin_yaw, -x * sin_yaw + z * cos_yaw
            y, z = y * cos_pitch - z * sin_pitch, y * sin_pitch + z * cos_pitch
            vertex = x, y, z


            projected_x = ((vertex[0] / vertex[2]) + 1) * CENTRE[0]
            projected_y = ((vertex[1] / vertex[2]) + 1) * CENTRE[1]

            # Frustum Culling - Don't render if not in view frustum
            if vertex[2] < 0.1:
                return None
            if 0 <= projected_x <= WIDTH or 0 <= projected_y <= HEIGHT:
                inside = True

            processed_face.append((int(projected_x), int(projected_y)))

        if not inside:
            return None

        depth = (relative_voxel_position[0]**2 + relative_voxel_position[1]**2 + relative_voxel_position[2]**2)

        return processed_face, depth


class Face:
    def __init__(self, position, index, type):
        self.position = position  # (x,y,z) of the origin of the face
        self.index = index  # Index of the face - Indexes into FACE_NORMALS
        self.colour = voxel_types[type - 1]
    
    def toCameraSpace(self, camera_position):
        # Translates the face from world space, with (0, 0, 0) at the origin,
        # to camera space, with (0, 0, 0) at the camera's position
        return (
            self.position[0] - camera_position[0],
            self.position[1] - camera_position[1],
            self.position[2] - camera_position[2])


pg.init()

screen = pg.display.set_mode((WIDTH, HEIGHT), flags=pg.DOUBLEBUF)

clock = pg.time.Clock()
previous_time = 0

camera = Camera((0, -2, 0), (0, 0, 0))
world = World()
renderer = Renderer(screen)

# Mouse lock
if GRAB_MOUSE:
    pg.mouse.set_visible(False)
    pg.event.set_grab(True)

running = True
# and previous_time <= 5000
while running:
    # Time and frame rate
    current_time = pg.time.get_ticks()
    delta = clamp(current_time - previous_time, 1, 9999)
    previous_time = current_time
    fps = round(clock.get_fps(), 2)

    # Player logic
    for event in pg.event.get():  
        if event.type == pg.MOUSEMOTION:
            relative_mouse_movement = event.rel
            camera.rotate(relative_mouse_movement, delta)
    keys = pg.key.get_pressed()

    if keys[pg.K_ESCAPE]:
        running = False

    camera.move(keys, 1/delta)

    world.update(camera)

    # Render
    screen.fill((32, 32, 32))
    renderer.render(world.mesh)
    pg.display.set_caption(f"Fps: {fps}")

    pg.display.flip()
    clock.tick(MAX_FPS)

pg.quit()
