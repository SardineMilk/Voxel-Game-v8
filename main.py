from settings import *

if PROFILE:
    import profiler
    profiler.profiler(sortby="tottime").start(True)


class Camera:
    def __init__(self, startingPosition, startingRotation):
        self.position = pg.Vector3(startingPosition)
        self.rotation = pg.Vector3(startingRotation)
    
    def moveCamera(self, keys, delta):
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

    def rotateCamera(self, mouse_movement, delta):
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
        self.chunks.append(Chunk((0, 0, 0)))

    def getVoxel(self, position):
        chunk_position, local_position = self.__worldToLocal(position)
        chunk = self.__getChunk(chunk_position)
        voxel = chunk.getVoxel(local_position)
        return voxel

    def setVoxel(self, position, type):
        chunk_position, local_position = self.__worldToLocal(position)
        chunk = self.__getChunk(chunk_position)
        chunk.setVoxel(local_position, type)

    def __getChunk(self, position):
        # If the chunk doesn't exist, load it
        chunk_index = self.__getChunkIndex(position)
        if chunk_index == None:
            self.__loadChunk(position)
            # loadChunk appends the chunk to the end of self.chunks
            # So it will be the last item in the list
            return self.chunks[-1]

        return self.chunks[chunk_index]

    def __getChunkIndex(self, position) -> int|None:
        # From a chunk position, get the 
        # Index of the chunk in the array of loaded chunks
        for index, chunk in enumerate(self.chunks):
            if chunk.position == tuple(position):  
                return index
        return None

    def __worldToLocal(self, position) -> tuple[list[int, int, int], list[int, int, int]]:
        # Convert a world position to a local position
        # Position of the chunk in 3d space
        chunk_index = [position[0] // CHUNK_SIZE, position[1] // CHUNK_SIZE, position[2] // CHUNK_SIZE]
        # Index of the voxel within the chunk
        local_index = [position[0] % CHUNK_SIZE, position[1] % CHUNK_SIZE, position[2] % CHUNK_SIZE]

        return chunk_index, local_index

    def constructMesh(self):
        mesh = []
        for chunk in self.chunks:
            mesh += chunk.constructMesh()
        return mesh
    
    def __loadChunk(self, position):
        # TODO - file opening
        self.chunks.append(Chunk(position))


class Chunk:
    def __init__(self, position):
        # Index of the chunk in 3d space - Tuple
        self.position = tuple(position)
        # Types of the voxels contained in the chunk - A flattened 1d numpy array of integers
        # It is stored this way for efficieny 
        self.voxels = np.zeros(CHUNK_VOLUME, dtype=int)
    
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

        mesh = []
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

                    mesh.append((voxel_world_pos, voxel_type, face_index))
        return mesh

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

    def __init__(self, surface) -> None:
        # The surface the renderer will draw on
        self.surface = surface
    
    def render(self, mesh):

        sorted_mesh = self.__sortVoxels(mesh)
        # Process the voxels
        processed_mesh = list(map(self.__processFace, sorted_mesh))  # List of quads and colours that must be drawn
        processed_mesh = filter(None, processed_mesh)

        if WIREFRAME:
            [gfxdraw.aapolygon(self.surface, points, WIREFRAME_COLOR) for points, color in processed_mesh]

        [pg.draw.polygon(self.surface, color, points) for points, color in processed_mesh]
        
    def __processFace(self, face):
        """
        - Translate face
        If face is visible:
        - Rotate
        - Project
        """
        voxel_position, voxel_type, face_index = face
        processed_face = []

        relative_voxel_position = voxel_position - camera.position

        is_visible = self.__checkVisibility(relative_voxel_position, face_index)

        if not is_visible:
            return None
        
        for vertex_index in FACES[face_index]:
            world_vertex = VERTICES[vertex_index]
            vertex = relative_voxel_position + world_vertex

            # Roll isn't needed

            # Rotate Pitch - Y
            vertex = vertex.rotate(-camera.rotation.x, pg.Vector3(0, 1, 0))
            # Rotate Yaw - X
            vertex = vertex.rotate(camera.rotation.y, pg.Vector3(1, 0, 0))
            
            # Frustum Culling - Don't render if behind camera
            if vertex.z <= FRUSTUM_TOLERANCE:
                return None

            projected_vertex = self.__project_vertex(vertex)

            processed_face.append(projected_vertex)

        voxel_color = voxel_types[int(voxel_type) - 1]
        return (tuple(processed_face), voxel_color)

    def __checkVisibility(self, voxel_position, face_index):
        """
        This function performs backface culling
        Backface culling - Cull faces where the normal isn't pointing towards the camera i.e facing away
        """
        face_normal = FACE_NORMALS[face_index]

        # By default, the voxel origin is the bottom front left corner.
        # If we leave it here, it will cause errors with backface culling
        # It is already relative to the camera
        voxel_centre = voxel_position + pg.Vector3(0.5, 0.5, 0.5)

        # Dot product of the face normal to the camera vector
        # If this is positive, they are pointing in roughly the same direction - <90 degrees
        # If it's negative, they are pointing roughly away from each other - >90 degrees
        # 3blue1brown has a wonderful linear algebra video explaining this: https://www.youtube.com/watch?v=LyGKycYT2v0
        face_to_camera = np.dot(face_normal, voxel_centre)

        # Use a slight bias to prevent shapes being culled too aggressively
        is_visible = face_to_camera <= -0.5

        return is_visible
    
    def __project_vertex(self, vertex):
        """
        As the z value of a vertex increases, it moves towards the centre of the screen
        We then multiply by half of the width|height to scale to the size of the window
        """

        x = ((vertex.x / vertex.z) + 1) * CENTRE[0]
        y = ((vertex.y / vertex.z) + 1) * CENTRE[1]

        return (x, y)
    
    def __sortVoxels(self, mesh):
        if INSERTION_SORT:
            # Traverse the mesh starting from the second face
            for i in range(1, len(mesh)):
                # Store the current face to be compared
                current_face = mesh[i]
                current_distance = (mesh[i][0]-camera.position).length_squared()
                # Initialize the position for comparison
                j = i - 1
                
                # Move the face that is closer one position ahead
                while j >= 0 and (mesh[j][0]-camera.position).length_squared() > current_distance:
                    mesh[j + 1] = mesh[j]
                    j -= 1
                
                # Place the current face in its correct position
                mesh[j + 1] = current_face
            return mesh
        return sorted(mesh, key=lambda position: (position[0]-camera.position).length_squared())[::-1]


pg.init()
screen = pg.display.set_mode((WIDTH, HEIGHT))
clock = pg.time.Clock()
previous_time = 0

camera = Camera((0, 0, 0), (0, 0, 0))
world = World()
renderer = Renderer(screen)

for i in range(32):
    for j in range(32):
            world.setVoxel((i, 0, j), randint(1, 3))


# Mouse lock
if GRAB_MOUSE:
    pg.mouse.set_visible(False)
    pg.event.set_grab(True)

geometry_changed = True

running = True
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
            camera.rotateCamera(relative_mouse_movement, delta)
    keys = pg.key.get_pressed()

    if keys[pg.K_ESCAPE]:
        running = False

    camera.moveCamera(keys, 1/delta)

    # Construct the mesh
    if geometry_changed:
        voxels_mesh = world.constructMesh()
        geometry_changed = False

    # Render
    screen.fill((32, 32, 32))
    renderer.render(voxels_mesh)

    pg.display.flip()
    #clock.tick(MAX_FPS)

pg.quit()
