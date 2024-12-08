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

    def getVoxel(self, position):
        chunk_position, local_position = self.__worldToLocal(position)
        chunk = self.__getChunk(chunk_position)
        voxel = chunk.getVoxel(local_position)
        return voxel

    def setVoxel(self, position, type):
        chunk_position, local_position = self.__worldToLocal(position)
        chunk = self.__getChunk(chunk_position)
        chunk.setVoxel(local_position, type)

    def updateRenderedChunks(self, player_pos):
        changed = False
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
                changed = True
                self.chunks.remove(chunk)
        
        for chunk_position in chunks_to_load:
            if self.__getChunkIndex(list(chunk_position)) == None:
                # If the chunk is not loaded, we load it
                changed = True
                self.__loadChunk(chunk_position)

        if changed:
            # If we've changed the loaded chunks, we remake the world
            self.constructMesh()

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
        self.voxels = self.procGen()
        self.constructMesh()
    
    def getVoxel(self, position):
        x, y, z = position
        # Range check - If it's outside the chunk, we return 0
        if ((0 <= x < CHUNK_SIZE) and
            (0 <= y < CHUNK_SIZE) and
            (0 <= z < CHUNK_SIZE)):

            index = self.__ToFlat(position)
            return self.voxels[index]

        return 0   
    
    def setVoxel(self, position, type):
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
        It takes the form of a list, with each element being:
        tuple(voxel_world_pos, voxel_type, face_index)

        The face_index determines which side of the voxel the face belongs to, with the lookup table stored in settings.py
        TODO move from settings.py

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
        index = int(index[0])  # index[0] because index is a numpy array, so it shouldnt be directly converted
        z = int(index / CHUNK_AREA)
        index -= z * CHUNK_AREA

        y = int(index / CHUNK_SIZE)

        x = int(index % CHUNK_SIZE)     

        return (x, y, z)   

    def procGen(self):
        voxels = np.zeros(CHUNK_VOLUME, dtype=int)
        for i in range(CHUNK_SIZE):
            for j in range(CHUNK_SIZE):
                if self.position[1] == 0:
                    index = self.__ToFlat((i, 0, j))
                    voxel_type =(math.sin(i*(0.1+self.position[0]))+math.sin(j*(0.1+self.position[2])))%4 +1
                    voxel_type = randint(1, 3)
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

        # We vectorise the processFace function using Numpy for performance reasons
        self.processMesh = np.vectorize(self.__processFace, otypes=[Face])
        # Vectorise the drawFace function
        self.drawMesh = np.vectorize(self.__drawFace)
    
    def render(self, mesh):
        if len(mesh) == 0:
            return
        
        if INSERTION_SORT:
            sorted_mesh = self.__sortMesh(mesh)
        else:
            sorted_mesh = mesh[np.argsort([-(face.position-camera.position).length_squared() for face in mesh])]
        # Process the voxels
        
        processed_mesh = self.processMesh(sorted_mesh)
        # Filter out None type - Faces that were culled in the processMesh function
        processed_mesh = processed_mesh[processed_mesh != None]
        #processed_mesh = list(map(self.__processFace, sorted_mesh))  # List of quads and colours that must be drawn
        #processed_mesh = filter(None, processed_mesh)

        if len(processed_mesh) == 0:
            return

        self.drawMesh(processed_mesh)
        
    def __processFace(self, face):
        #TODO move into Face class
        """
        - Translate face
        If face is visible:
        - Rotate
        - Project
        """
        
        world_voxel_position = face.position - camera.position

        is_visible = self.__checkVisibility(world_voxel_position, tuple(FACE_NORMALS[face.index]))

        if not is_visible:
            return None
        
        processed_face = [0]*4
        face_vertex_indices = FACES[face.index]
        for i, vertex_index in enumerate(face_vertex_indices):
            model_vertex_position = VERTICES[vertex_index]  # Indexes into the VERTICES array
            vertex = world_voxel_position + model_vertex_position
            # TODO Scale to face size

            # Rotate Pitch - Y
            vertex = vertex.rotate(-camera.rotation.x, pg.Vector3(0, 1, 0))
            # Rotate Yaw - X
            vertex = vertex.rotate(camera.rotation.y, pg.Vector3(1, 0, 0))

            # Frustum Culling - Don't render if behind camera or too far away
            if vertex.z <= NEAR:
                return None

            # This function will crash if given (*, * 0) as the vertex, but due to the Frustum Culling step, that will never happen
            projected_vertex = self.__projectVertex(vertex)

            processed_face[i] = (projected_vertex.x, projected_vertex.y)

        return (tuple(processed_face), face.colour)

    def __sortMesh(self, mesh):
        """
        Custom Insertion Sort algorithm that runs if the setting INSERTION_SORT is set to True
        """
        # Traverse the mesh starting from the second face
        for i in range(1, len(mesh)):
            current_face = mesh[i]
            j = i-1
            # If the distance to the comparison face is less than current_face, swap them
            while j >=0 and ((current_face.position-camera.position).length_squared() >= (mesh[j].position-camera.position).length_squared()):
                mesh[j+1] = mesh[j]
                j -= 1
            mesh[j+1] = current_face
        return np.array(mesh)

    def __drawFace(self, face):
        points, color = face
        pg.draw.polygon(self.surface, color, points, width=WIREFRAME)

    def __projectVertex(self, vertex):
        # Call the function projectVertex, written in C to improve performance.
        return c_functions.projectVertex(Vector3D(vertex[0], vertex[1], vertex[2]), Vector2D(CENTRE[0], CENTRE[1]))

    def __checkVisibility(self, position, normal):
        return c_functions.checkVisibility(Vector3D(position[0], position[1], position[2]),
                                                 Vector3D(normal[0], normal[1], normal[2]))


class Face:
    def __init__(self, position, index, type):
        self.position = position  # (x,y,z) of the origin of the face
        self.index = index  # Index of the face - Indexes into FACE_NORMALS
        self.colour = voxel_types[type - 1]


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

geometry_changed = True

running = True
# and previous_time <= 5000
while running:
    # Time and frame rate
    current_time = pg.time.get_ticks()
    delta = clamp(current_time - previous_time, 1, 9999)
    previous_time = current_time
    fps = round(1000/delta, 2)

    # Player logic
    for event in pg.event.get():  # Movement breaks without this for some reason
        if event.type == pg.MOUSEMOTION:
            relative_mouse_movement = event.rel
            camera.rotate(relative_mouse_movement, delta)
    keys = pg.key.get_pressed()

    if keys[pg.K_ESCAPE]:
        running = False

    camera.move(keys, 1/delta)
    camera.position.z += 10

    world.updateRenderedChunks(camera.position)

    # Render
    screen.fill((32, 32, 32))
    renderer.render(world.mesh)

    print(fps, camera.position.z)

    pg.display.flip()
    clock.tick(MAX_FPS)

pg.quit()
