from settings import *


class Camera:
    def __init__(self, starting_position: pg.Vector3, starting_rotation: pg.Vector3):
        self.position = pg.Vector3(starting_position)
        self.rotation = pg.Vector3(starting_rotation)
    
    def move(self, keys, delta: int):
        # Requirement - U3

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
        # Requirement - U3

        yaw   = mouse_movement[0] * PLAYER_ROTATION_SENSITIVITY * (delta / 1000)
        pitch = mouse_movement[1] * PLAYER_ROTATION_SENSITIVITY * (delta / 1000)

        rotation_vector = pg.Vector3((yaw, pitch, 0))
        # Add the rotation vector to the player rotation 
        self.rotation = self.rotation + rotation_vector
        # Clamp the pitch to directly up/down
        self.rotation.y = clamp(self.rotation.y, -90, 90)
    

class World:
    def __init__(self, name):
        self.name = name
        self.chunks = []
        self.changed = True  # If any chunk meshes have changed, we set this to tre

    def getVoxel(self, position):
        chunk_position, local_position = self.__worldToLocal(position)
        chunk = self.__getChunk(chunk_position)
        voxel = chunk.getVoxel(local_position)
        return voxel

    def setVoxel(self, position, type):
        chunk_position, local_position = self.__worldToLocal(tuple(position))
        chunk = self.__getChunk(chunk_position)
        chunk.setVoxel(local_position, type)
        self.changed = True

    def update(self, camera):
        self.updateRenderedChunks(camera.position)
        if self.changed:
            self.constructMesh()
        self.changed = False

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
                self.unloadChunk(chunk.position)

        for chunk_position in chunks_to_load:
            if self.__getChunkIndex(list(chunk_position)) == None:
                # If the chunk is not loaded, we load it
                self.changed = True
                self.loadChunk(chunk_position)

    def constructMesh(self):
        mesh = []
        for chunk in self.chunks:
            mesh += chunk.mesh
        self.mesh = np.array(mesh, dtype=Face)
    
    def __getChunk(self, position:tuple[int, int, int]):
        # If the chunk doesn't exist, load it
        chunk_index = self.__getChunkIndex(position)
        if chunk_index == None:
            self.loadChunk(position)
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

    def loadChunk(self, position):
        # Requirement - U2
        try:
            # Load chunk data from file
            file_name = self.__getFilePath(str(tuple(position)))+".npy"
            voxels = np.load(file_name)
        except OSError:
            voxels = terrain_generator.generateChunk(position)

        self.chunks.append(Chunk(position, voxels))

    def unloadChunk(self, position):
        # Requirement - U2
        # Unload a chunk, saving it to file
        chunk = self.__getChunk(position)

        file_name = self.__getFilePath(str(tuple(position)))
        np.save(file_name, chunk.voxels)

        self.chunks.remove(chunk)

    def __getFilePath(self, file_name):
        return self.name + "/" + file_name


class Chunk:
    def __init__(self, position, voxels):
        # Index of the chunk in 3d space - Tuple
        self.position = tuple(position)
        # Types of the voxels contained in the chunk - A flattened 1d numpy array of integers
        # It is stored this way for efficiency - both time and space 
        self.voxels = voxels
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

            index = toFlat(position)
            return self.voxels[index]

        return 0  # If position is outside chunk, assume it's empty to prevent holes in the terrain
    
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
                index = toFlat(position)
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
            voxel_pos = pg.Vector3(to3d(voxel_index))

            for face_index, face_normal in enumerate(FACE_NORMALS):
                # Interior Face Culling
                check_pos = voxel_pos + face_normal
                neighbour_type = self.getVoxel(check_pos)
                if neighbour_type == 0:
                    
                    voxel_world_pos = tuple((chunk_offset + pg.Vector3(voxel_pos)))

                    voxel_type = self.getVoxel(voxel_pos)

                    self.mesh.append(Face(voxel_world_pos, face_index, voxel_type))


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
        
        processed_mesh = processMesh(mesh, tuple(player.position), tuple(player.rotation))

        if len(processed_mesh) == 0:
            return
        
        if INSERTION_SORT:
            sorted_mesh = self.__sortFaces(processed_mesh)
        else:
            sorted_mesh = sorted(processed_mesh, key=lambda x: x[2])[::-1]


        for face in sorted_mesh:
            pg.draw.polygon(self.surface, face[1], face[0], width=WIREFRAME)

    def __drawFace(self, face):
        points, color = face
        pg.draw.polygon(self.surface, color, points, width=WIREFRAME)

    def __sortFaces(self, mesh):
        # Sort the mesh based on depth in reverse order
        for i in range(1, len(mesh)):
            j = i
            temp = mesh[i]
            while j >= 0 and mesh[j-1][2] < temp[2]:
                mesh[j] = mesh[j-1]
                j -= 1
            mesh[j] = temp
        return mesh


class Face:
    def __init__(self, position, index, type):
        self.index = index
        self.position = position  # (x,y,z) of the origin of the face
        self.normal = FACE_NORMALS[index]  # Index of the face - Indexes into FACE_NORMALS
        self.mesh = self.__generateMesh()

        self.colour = voxel_types[type - 1]

    def __generateMesh(self):
        vertex_indices = FACES[self.index]
        mesh = np.empty((4, 3), dtype=np.float32)
        for i, vertex_index in enumerate(vertex_indices):
            vertex = VERTICES[vertex_index]

            translated_vertex = np.array((
                vertex[0] + self.position[0],
                vertex[1] + self.position[1],
                vertex[2] + self.position[2],
            ), dtype=np.float32)

            mesh[i] = np.array(translated_vertex, dtype=np.float32)

        return mesh
        


class TerrainGenerator:
    def sample(self, position):
        if position[1] == 0:
            voxel_type = (math.sqrt(((position[0]*CHUNK_SIZE)**2)+
                            ((position[2]*CHUNK_SIZE)**2))//2
                ) %3+1
            return voxel_type
        else:
            return 0

    
    def generateChunk(self, position):
        voxels = np.zeros(CHUNK_VOLUME, dtype=np.uint8)  # Int8 is used to decrease memory usage - much smaller than float
        for x in range(CHUNK_SIZE):
            for y in range(CHUNK_SIZE):
                    for z in range(CHUNK_SIZE):
                        world_x = x + (position[0]*CHUNK_SIZE)
                        world_y = y + (position[1]*CHUNK_SIZE)
                        world_z = z + (position[2]*CHUNK_SIZE)

                        voxel_type = self.sample((world_x, world_y, world_z))

                        index = toFlat((x, y, z))

                        voxels[index] = np.int16(voxel_type)
        return voxels


class Player(Camera):
    def __init__(self, starting_position, starting_rotation):
        super().__init__(starting_position, starting_rotation)

    def updateVoxelType(self, mouse_wheel_y):
            self.voxel_type += mouse_wheel_y

            # If it goes out of bounds, loop to the other end of list
            if self.voxel_type > len(voxel_types) - 1:
                self.voxel_type = 0
            if self.voxel_type < 1:
                # 1 is used because 0 is empty, bound to left click
                self.voxel_type = len(voxel_types) - 1
    
    def placeVoxels(self):
        # Requirement - U1
        
        # Voxel Placing - TODO complete
        placing_pos = (int(self.position.x), int(self.position.y), int(self.position.z))
        if pg.mouse.get_pressed()[2]:
            world.setVoxel(placing_pos , self.voxel_type)
        if pg.mouse.get_pressed()[0]:
            world.setVoxel(placing_pos, 0)



def processMesh(mesh, camera_position, camera_rotation):
    # Using the mesh, return a list of faces that must be drawn
    processed_mesh = []  # (Points, Colour, Depth)

    # These values are unique to each frame, so computing them per face is redundant
    sin_yaw =   math.sin(math.radians(-camera_rotation[0]))
    cos_yaw =   math.cos(math.radians(-camera_rotation[0]))
    sin_pitch = math.sin(math.radians(camera_rotation[1]))
    cos_pitch = math.cos(math.radians(camera_rotation[1]))
    
    for face in mesh:
        processed_face = processFace(face.mesh, face.position, face.normal, camera_position, sin_yaw, cos_yaw, sin_pitch, cos_pitch)
        if processed_face != None:
            points, depth = processed_face
            processed_mesh.append((points, face.colour, depth))
    return processed_mesh

@njit(fastmath=True)
def processFace(face_mesh, voxel_position, face_normal, camera_position, sin_yaw, cos_yaw, sin_pitch, cos_pitch):
        """
        - Check backface visibility
        If face is visible:
            - Rotate
            - Project
            - Return processed_face
        """

        is_visible = checkBackfaceVisibility(face_normal, voxel_position, camera_position)
        
        # If it's not visible, skip the rest of the function
        if not is_visible:
            return None

        # processed_face will always have length 4, so .append() is not needed
        processed_face = np.empty((4, 2), dtype=np.int32)

        inside = False  # Flag that stores if any vertices of the face are inside the window

        for i, vertex in enumerate(face_mesh):
            translated_vertex = (
                vertex[0] - camera_position[0],
                vertex[1] - camera_position[1],
                vertex[2] - camera_position[2],
            )

            x, y, z = translated_vertex
            x, z = x * cos_yaw + z * sin_yaw, -x * sin_yaw + z * cos_yaw
            y, z = y * cos_pitch - z * sin_pitch, y * sin_pitch + z * cos_pitch
            rotated_vertex = x, y, z

            # Frustum Culling - Don't render if not in view frustum
            if rotated_vertex[2] < NEAR:
                return None
            
            projected_x, projected_y = projectVertex(rotated_vertex)

            # If any vertex is inside the window, render the face
            if 0 <= projected_x <= WIDTH or 0 <= projected_y <= HEIGHT:
                inside = True

            processed_face[i][0] = np.int32(projected_x)
            processed_face[i][1] = np.int32(projected_y)

        # If no vertices are inside the window, don't render the face
        if not inside:
            return None

        # Since only the relative depth matters, we can skip the costly sqrt() function
        depth = ((voxel_position[0] - camera_position[0])**2 + (voxel_position[1] - camera_position[1])**2 + (voxel_position[2] - camera_position[2])**2)
        #depth = np.linalg.norm(relative_voxel_position)

        return processed_face, depth


@njit(fastmath=True)
def checkBackfaceVisibility(normal, voxel_position, camera_position):
        face_to_camera = (
                        (voxel_position[0] - camera_position[0]) * normal[0] +
                        (voxel_position[1] - camera_position[1]) * normal[1] +
                        (voxel_position[2] - camera_position[2]) * normal[2] 
                        )
        is_visible =  (face_to_camera <= -0.5)
        return is_visible
        
@njit(fastmath=True)
def projectVertex(vertex):
    projected_x = ((vertex[0] / vertex[2]) + 1) * CENTRE[0]
    projected_y = ((vertex[1] / vertex[2]) + 1) * CENTRE[1]
    return projected_x, projected_y

def fetchVoxelTypesFromDatabase():
    # Query the database for existing voxel types
    return 

def addVoxelTypeToDatabase(voxel_colour, transparent):
    # Append a new voxel type to the database
    pass

pg.init()

screen = pg.display.set_mode((WIDTH, HEIGHT), flags=pg.DOUBLEBUF)

clock = pg.time.Clock()
previous_time = 0

held_voxel_type = 1
world_name = "world1"

player = Player((0, -2, 0), (0, 0, 0))
player.voxel_type = held_voxel_type

world = World(world_name)
renderer = Renderer(screen)
terrain_generator = TerrainGenerator()


# Mouse lock>>
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
        # Camera Rotation
        if event.type == pg.MOUSEMOTION:
            relative_mouse_movement = event.rel
            player.rotate(relative_mouse_movement, delta)

        # Voxel Type 
        if event.type == pg.MOUSEWHEEL:
            player.updateVoxelType(event.y)


    keys = pg.key.get_pressed()

    if keys[pg.K_ESCAPE]:
        running = False
    
    player.move(keys, 1/delta)
    player.placeVoxels()

    world.update(player)

    # Render
    screen.fill(SKY_COLOR)
    renderer.render(world.mesh)
    pg.display.set_caption(f"Fps: {fps}")

    pg.display.flip()
    clock.tick(MAX_FPS)


for chunk in world.chunks:
    world.unloadChunk(chunk.position)

pg.quit()
