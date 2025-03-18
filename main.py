from settings import *


class Camera:
    def __init__(self, starting_position: pg.Vector3, starting_rotation: pg.Vector3):
        self.position = pg.Vector3(starting_position)  #(x, y, z)
        self.rotation = pg.Vector3(starting_rotation)  #(yaw, pitch, roll)
    
    def move(self, keys, delta):
        # Requirement - U3
        # Requirement - FI1

        delta_factor = (1/delta)*1000
        speed = PLAYER_SPEED / (delta_factor)
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
        # Requirement - FI2

        yaw   = mouse_movement[0] * PLAYER_ROTATION_SENSITIVITY * (delta / 1000)
        pitch = mouse_movement[1] * PLAYER_ROTATION_SENSITIVITY * (delta / 1000)

        rotation_vector = pg.Vector3((yaw, pitch, 0))
        # Add the rotation vector to the player rotation 
        self.rotation = self.rotation + rotation_vector
        # Clamp the pitch to directly up/down
        self.rotation.y = clamp(self.rotation.y, -90, 90)
    

class World:
    def __init__(self, name, chunk_size):
        self.name = name
        self.chunks = []
        self.changed = True  # Flag to reconstruct mesh - set to true if any chunk meshes are changed

    def updateVoxelList(self):
        raw_voxel_list = database.fetchVoxelTypes()

        self.voxel_types = []
        for raw_voxel in raw_voxel_list:
            self.voxel_types.append(raw_voxel[1:4])

    def getVoxel(self, position):
        # Get the voxel type at a specific world position
        chunk_position, local_position = self.__worldToLocal(position)
        chunk = self.__getChunk(chunk_position)
        voxel = chunk.getVoxel(local_position)
        return voxel

    def setVoxel(self, position, type):
        # Set the voxel type at a specific world position
        chunk_position, local_position = self.__worldToLocal(tuple(position))
        chunk = self.__getChunk(chunk_position)
        chunk.setVoxel(local_position, type)
        self.changed = True

    def update(self, camera):
        # Update loaded chunks based on player position
        self.updateRenderedChunks(camera.position)  # Requirement - FP7
        # Reconstruct mesh if needed
        if self.changed:
            self.constructMesh()  # Requirement - FP8
        self.changed = False

    def updateRenderedChunks(self, player_pos):
        # Requirement - U5

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

        # Load needed chunks that are currently unloaded
        for chunk_position in chunks_to_load:
            if self.__getChunkIndex(list(chunk_position)) == None:
                # If the chunk is not loaded, we load it
                self.changed = True
                self.loadChunk(chunk_position)

    def constructMesh(self):
        # Build the world mesh from existing chunk meshes
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

        # Return the requested chunk
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
            # If the file does not exist, generate a new chunk
            voxels = terrain_generator.generateChunk(position)

        self.chunks.append(Chunk(position, voxels))

    def unloadChunk(self, position):
        # Requirement - U2
        # Unload a chunk, saving it to file
        chunk = self.__getChunk(position)

        # If the folder to save in doesn't exist,
        if not os.path.exists(self.name):
            # Create it
            os.makedirs(self.name)

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
        # Fetch the voxel data at an (x, y, z) position in the chunk

        x, y, z = position
        # Range check - If it's outside the chunk, we return 0
        if ((0 <= x < CHUNK_SIZE) and
            (0 <= y < CHUNK_SIZE) and
            (0 <= z < CHUNK_SIZE)):

            index = toFlat(position)
            return self.voxels[index]

        return 0  # If position is outside chunk, assume it's empty to prevent holes in the terrain
    
    def setVoxel(self, position, type):
        # Set the voxel data at an (x, y, z) position in the chunk
        # Then rebuild the chunk mesh

        x, y, z = position
        # Range check - Is it inside the chunk?
        if (0 <= x <= CHUNK_SIZE - 1 or 
            0 <= y <= CHUNK_SIZE - 1 or
            0 <= z <= CHUNK_SIZE - 1):
                index = toFlat(position)
                self.voxels[index] = type
                self.constructMesh()

    def constructMesh(self):
        # This constructs the chunk mesh
        # It takes the form of a list, with each element being a Face object
        # The face_index determines which side of the voxel the face belongs to, with the lookup table stored in settings.py

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

    It then renders the UI involving:
        - Crosshair
        - FPS
        - Held voxel indicator
    """
    def __init__(self, surface, sky_colour):
        self.surface = surface  # The surface the renderer will draw on
        self.sky_colour = sky_colour  # The background colour
    
    def render(self, mesh):
        self.surface.fill(SKY_COLOR)

        self.renderMesh(mesh)

        self.renderUI()

    def renderMesh(self, mesh):
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
            # Requirement - FO1
            pg.draw.polygon(self.surface, face[1], face[0], width=WIREFRAME)
            if OUTLINE:
                gfxdraw.aapolygon(self.surface, face[0], (0, 0, 0))

    def renderUI(self):
        # Requirement - U6
        # Requirement - FO2

        # Crosshair
        pg.draw.circle(self.surface,  (255, 255, 255), CENTRE, 1)        

        # Held Voxel
        pg.draw.rect(self.surface, (0, 0, 0), ((0, HEIGHT-127), (127, 127)), 2)
        pg.draw.rect(self.surface, world.voxel_types[player.voxel_type-1], ((0, HEIGHT-125), (125, 125)))

        # FPS text
        text = font.render(f"FPS: {str(fps)}", True, (255, 255, 255))
        screen.blit(text)

    def __sortFaces(self, mesh):
        # Requirement - FP10
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
        """
        The colour/type is technically uneeded, as world.getVoxel(voxel_world_pos) can be called to get the type
        However, it gives a massive performance boost due to preventing redundant calculations
        """
        self.position = position  # (x,y,z) of the origin of the face
        self.normal = FACE_NORMALS[index]  # Index of the face - Indexes into FACE_NORMALS
        self.__index = index

        self.colour = world.voxel_types[type - 1]

        self.mesh = self.__generateMesh()

    def __generateMesh(self):
        vertex_indices = FACES[self.__index]
        mesh = np.empty((4, 3), dtype=np.float32)
        for i, vertex_index in enumerate(vertex_indices):
            vertex = VERTICES[vertex_index]

            translated_vertex = np.array((
                vertex[0] + self.position[0],
                vertex[1] + self.position[1],
                vertex[2] + self.position[2],
            ), dtype=np.float32)

            mesh[i] = translated_vertex

        return mesh


class TerrainGenerator:
    def __init__(self, seed):
        self.seed = seed
        
    def sample(self, position):
        if position[1] == 0:
            voxel_type = (math.sqrt(((position[0]*CHUNK_SIZE)**2)+
                            ((position[2]*CHUNK_SIZE)**2))//2
                ) % (len(world.voxel_types)) + 1
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
        self.voxel_type = 1

    def updateVoxelType(self, mouse_wheel_y):
            # Requirement - FI4

            self.voxel_type += mouse_wheel_y

            # If it goes out of bounds, loop to the other end of list
            if self.voxel_type > len(world.voxel_types):
                self.voxel_type = 1
            if self.voxel_type < 1:
                # 1 is used because 0 is empty, bound to left click
                self.voxel_type = len(world.voxel_types) 
    
    def placeVoxels(self):
        # Requirement - U1
        
        # Voxel Placing - TODO complete
        placing_pos = (int(self.position.x), int(self.position.y), int(self.position.z))
        # Requirement - FI3
        if pg.mouse.get_pressed()[2]:  # Right click
            world.setVoxel(placing_pos , self.voxel_type)
        # Requirement - FI3
        if pg.mouse.get_pressed()[0]:  # Left click
            world.setVoxel(placing_pos, 0)


class DatabaseManager:
    def connectToWorldsDatabase(self):
        # Attempt to connect to worlds database
        self.worlds_database = self.__connectToDatabase("WorldsData", self.createNewWorldsDatabase)

    def connectToVoxelsDatabase(self, world_name):
        # Attempt to connect to voxels database
        self.voxels_database = self.__connectToDatabase(f"{world_name}_VoxelsData", self.createNewVoxelsDatabase)

    def __connectToDatabase(self, database_name, create_database_func):
        retry_attempts = 3
        for i in range(retry_attempts):
            print(f"Attempting to connect to {database_name} database: attempt {i}")
            try:
                connection = mysql.connector.connect(
                    host="localhost",
                    user="root",
                    password="root",
                    database=database_name
                    )
                print(f"Connected to {database_name} database")
                return connection
            except mysql.connector.Error as e:
                print(f"Could not connect to {database_name} database: {e}")
                print(f"Creating new {database_name} database")
                create_database_func()

        raise Exception(f"Failed to connect to {database_name} after {retry_attempts} attempts")

    def fetchWorld(self, world_name):
        with self.worlds_database.cursor() as worlds_cursor:
            worlds_cursor.execute("SELECT * FROM worlds WHERE world_name = %s", 
                                (world_name,))
            result = worlds_cursor.fetchall()

        # Raise an exception if the world doesn't exist
        # This means other functions can create a new world rather than using the empty list
        if len(result) == 0:
            raise Exception(f"{world_name} does not exist")

        return result

    def fetchVoxelTypes(self):
        # Query the database for existing voxel types
        with self.voxels_database.cursor() as voxels_cursor:
            voxels_cursor.execute("SELECT * FROM voxel_types")
            result = voxels_cursor.fetchall()
        return result

    def addWorld(self, world_name, chunk_size, sky_colour, world_seed):
        with self.worlds_database.cursor() as worlds_cursor:
            worlds_cursor.execute("INSERT INTO worlds (world_name, chunk_size, sky_colour_r, sky_colour_g, sky_colour_b, world_seed) VALUES (%s, %s, %s, %s, %s, %s)",
                                    (world_name, chunk_size, sky_colour[0], sky_colour[1], sky_colour[2], world_seed))

    def addVoxelType(self, voxel_colour, transparent):
        # Append a new voxel type to the database
        with self.voxels_database.cursor() as voxels_cursor:
            voxels_cursor.execute("INSERT INTO voxel_types (red, green, blue, transparent) VALUES (%s, %s, %s, %s)", 
                                (voxel_colour[0], voxel_colour[1], voxel_colour[2], transparent))

    def createNewWorldsDatabase(self):
        try:
            # Connect to MySQL server (generic, not any specific database)
            mysql_connection = mysql.connector.connect(
                host="localhost",
                user="root",
                password="root"
            )
            cursor = mysql_connection.cursor()
            
            # Create database
            cursor.execute("CREATE DATABASE IF NOT EXISTS WorldsData")
            
            # Connect to the new database
            mysql_connection.database = "WorldsData"
            
            # Create Worlds Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS worlds (
                    world_id INT AUTO_INCREMENT PRIMARY KEY,
                    world_name VARCHAR(20) NOT NULL,
                    chunk_size INT NOT NULL,
                    sky_colour_r INT NOT NULL,
                    sky_colour_g INT NOT NULL,
                    sky_colour_b INT NOT NULL,
                    world_seed INT NOT NULL
                )""")
            
            # Commit connection
            mysql_connection.commit()

        except mysql.connector.Error as e:
            print(f"Error creating WorldsData database: {e}")
        
        finally:
            if mysql_connection.is_connected():
                cursor.close()
                mysql_connection.close()


    def createNewVoxelsDatabase(self):
        database_name = f"{self.world_name}_VoxelsData"

        try:
            # Connect to MySQL server (generic, not any specific database)
            mysql_connection = mysql.connector.connect(
                host="localhost",
                user="root",
                password="root"
            )
            cursor = mysql_connection.cursor()
            
            # Create database
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database_name}")
            
            # Connect to the new database
            mysql_connection.database = database_name
            
            # Create Voxels Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS voxel_types (
                    voxel_id INT AUTO_INCREMENT PRIMARY KEY,
                    red INT NOT NULL,
                    green INT NOT NULL,
                    blue INT NOT NULL,
                    transparent BOOLEAN NOT NULL
                )""")
            
            # Commit connection
            mysql_connection.commit()

        except mysql.connector.Error as e:
            print(f"Error creating {database_name} database: {e}")

        finally:
            if mysql_connection.is_connected():
                cursor.close()
                mysql_connection.close()

    def close(self):
        self.worlds_database.commit()
        self.worlds_database.close()

        self.voxels_database.commit()
        self.voxels_database.close()

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
        # Requirement - FP9
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

            # Frustum Culling - Don't render if not in view frustum (behind camera)
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


def inputNewVoxel():
    # Unlock the mouse
    pg.mouse.set_visible(True)
    pg.event.set_grab(False)

    inputWindow = tk.Tk()
    inputWindow.title("Add New Voxel")

    # Inputs
    tk.Label(inputWindow, text="Red Value (0-255):").pack(pady=2)
    r_entry = tk.Entry(inputWindow, width=30)
    r_entry.pack(pady=2)

    tk.Label(inputWindow, text="Green Value (0-255):").pack(pady=2)
    g_entry = tk.Entry(inputWindow, width=30)
    g_entry.pack(pady=2)

    tk.Label(inputWindow, text="Blue Value (0-255):").pack(pady=2)
    b_entry = tk.Entry(inputWindow, width=30)
    b_entry.pack(pady=2)

    transparent_bool = tk.BooleanVar()
    tk.Label(inputWindow, text="Is the voxel transparent?").pack(pady=2)
    transparent_checkbox = tk.Checkbutton(inputWindow, text="Transparent?", variable=transparent_bool)
    transparent_checkbox.pack(pady=2)

    def submit():
        # This repeats until a valid input is detected
        try:
            # Get the rgb values
            # This raises an error if any are null
            r = int(r_entry.get())
            g = int(g_entry.get())
            b = int(b_entry.get())

            # Validate all rgb values are in range
            if not (0 <= r <= 255):
                raise ValueError("Red value must be between 0 and 255.")
            if not (0 <= g <= 255):
                raise ValueError("Green value must be between 0 and 255.")
            if not (0 <= b <= 255):
                raise ValueError("Blue value must be between 0 and 255.")

            transparent = transparent_bool.get()

            database.addVoxelType((r, g, b), transparent)

            inputWindow.destroy()  # Close the window after successful input

        except ValueError as e:
            print(f"Invalid Input: {str(e)}")

    # Submit Button
    submit_button = tk.Button(inputWindow, text="Submit", command=submit)
    submit_button.pack(pady=10)

    inputWindow.mainloop()

    # Lock the mouse again
    pg.mouse.set_visible(False)
    pg.event.set_grab(True)

    # Update the world's list of voxels
    world.updateVoxelList()


def getWorld():
    # Unlock the mouse
    pg.mouse.set_visible(True)
    pg.event.set_grab(False)

    inputWindow = tk.Tk()
    inputWindow.title("Open/Create World")

    # Inputs
    tk.Label(inputWindow, text="Enter the world name:").pack(pady=2)
    world_var = tk.StringVar()
    world_entry = tk.Entry(inputWindow, textvariable=world_var, width=30)
    world_entry.pack(pady=2)


    def submit():
        # This repeats until a valid input is detected
        try:
            world_name = world_var.get().strip()

            # Validate the world_name is the correct length
            if not (1 <= len(world_name) <= 20):
                raise ValueError("World name must be between 1 and 20 characters")

            inputWindow.destroy()  # Close the window after successful input

        except ValueError as e:
            print(f"Invalid Input: {str(e)}")

    # Submit Button
    submit_button = tk.Button(inputWindow, text="Submit", command=submit)
    submit_button.pack(pady=10)

    inputWindow.mainloop()

    world_name = world_var.get().strip()

    # Lock the mouse again
    pg.mouse.set_visible(False)
    pg.event.set_grab(True)

    # Get the world if possible, or create new world
    try:
        world = database.fetchWorld(world_name)
        print(f"Fetched world {world_name}")
    except:
        print(f"Could not fetch world {world_name}")
        print("Creating new world")
        database.addWorld(world_name, 16, (SKY_COLOR), 1)
        world = database.fetchWorld(world_name)

    world_id, world_name, chunk_size, sky_r, sky_g, sky_b, world_seed = world[0]

    return world_name, chunk_size, (sky_r, sky_g, sky_b), world_seed

pg.init()

world_name = "world1"

# Initialise: Requirement - FP1
screen = pg.display.set_mode((WIDTH, HEIGHT), flags=pg.DOUBLEBUF)
font = pg.font.Font(None, 24)
clock = pg.time.Clock()
previous_time = 0

database = DatabaseManager()  # Requirement - FP3
database.connectToWorldsDatabase()  # The Worlds database is needed for the getWorld() function
world_name, chunk_size, sky_colour, world_seed = getWorld()
database.world_name = world_name
database.connectToVoxelsDatabase(world_name)

player = Player((0, -2, 0), (0, 0, 0)) # Requirement - FP2
renderer = Renderer(screen, sky_colour)
world = World(world_name, chunk_size)
terrain_generator = TerrainGenerator(world_seed)

world.updateVoxelList()
if len(world.voxel_types) == 0:
    inputNewVoxel()

pg.display.set_caption(f"Voxel Game: {world.name}")

# Mouse lock
if GRAB_MOUSE:
    pg.mouse.set_visible(False)
    pg.event.set_grab(True)

running = True
while running:
    # Time and frame rate
    current_time = pg.time.get_ticks()
    delta = max(current_time - previous_time, 1)
    previous_time = current_time
    fps = round(clock.get_fps(), 2)

    # Player logic: Requirement - FP5
    for event in pg.event.get():  
        # Camera Rotation
        if event.type == pg.MOUSEMOTION:
            relative_mouse_movement = event.rel
            player.rotate(relative_mouse_movement, delta)

        # Voxel Type - Changes with scroll wheel
        if event.type == pg.MOUSEWHEEL:
            player.updateVoxelType(event.y)

        if event.type == pg.KEYDOWN:
            if event.key == pg.K_e:
                WIREFRAME = not WIREFRAME
            
            if event.key == pg.K_r:
                inputNewVoxel()

    keys = pg.key.get_pressed()

    # Quit the game if the escape key is pressed
    if keys[pg.K_ESCAPE]:
        running = False
    
    # Requirement - FP5
    player.move(keys, delta)
    player.placeVoxels()

    world.update(player)

    # Render
    renderer.render(world.mesh)

    pg.display.flip()
    clock.tick(MAX_FPS)

# Unloading the chunks saves them to file, meaning the game autosaves whenever you quit
for chunk in world.chunks:
    world.unloadChunk(chunk.position)

database.close()

pg.quit()
