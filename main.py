from settings import *

if PROFILE:
    import profiler
    profiler.profiler().start(True)


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
        self.chunks.append(Chunk(0, 0, 0))


class Chunk:
    def __init__(self, position):
        self.position = position
        self.voxels = np.zeros((CHUNK_SIZE, CHUNK_SIZE, CHUNK_SIZE))
    
    def setVoxel(self, position, type):
        x, y, z = position
        x, y, z = int(x), int(y), int(z)

        # Range check - Is it inside the chunk?
        if (0 <= x <= CHUNK_SIZE - 1 or 
            0 <= y <= CHUNK_SIZE - 1 or
            0 <= z <= CHUNK_SIZE - 1):
                self.voxels[x, y, z] = type

    def getVoxel(self, position):
        x, y, z = position
        x, y, z = int(x), int(y), int(z)

        # Range check - If it's outside the chunk, we return 0
        if ((0 > x or x > CHUNK_SIZE - 1) or 
            (0 > y or y > CHUNK_SIZE - 1) or
            (0 > z or z > CHUNK_SIZE - 1)):
            return 0

        return self.voxels[x, y, z]
    
    def constructMesh(self):
        mesh = []
        filtered_voxels = np.argwhere(self.voxels != 0)
        for voxel_pos in filtered_voxels:
            voxel_pos = pg.Vector3(tuple(voxel_pos))
            for face_index, face_normal in enumerate(FACE_NORMALS):
                # Interior Face Culling
                check_pos = voxel_pos + face_normal

                try:
                    neighbour_type = self.getVoxel(check_pos)
                except IndexError:
                    # TODO - neighbouring chunks
                    neighbour_type = 0

                if neighbour_type == 0:
                    mesh.append((voxel_pos, face_index))
        return mesh


class Renderer:
    def render(self, mesh):
        sorted_mesh = self.sortVoxels(mesh)
        # Process the voxels
        processed_mesh = list(map(self.processFace, sorted_mesh))  # List of quads and colours that must be drawn
        processed_mesh = filter(None, processed_mesh)

        # Render
        screen.fill((32, 32, 32))

        if WIREFRAME:
            [gfxdraw.aapolygon(screen, points, (0, 255, 0)) for points, color in processed_mesh]

        [pg.draw.polygon(screen, color, points) for points, color in processed_mesh]
        
    def processFace(self, face):
        voxel_position, face_index = face
        voxel_type = world.getVoxel(voxel_position)
        processed_face = []

        relative_voxel_position = voxel_position - camera.position

        is_visible = self.checkVisibility(relative_voxel_position, face_index)

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

            projected_vertex = self.project_vertex(vertex)


            processed_face.append(projected_vertex)

        
        if len(processed_face) != 4:
            return None
        
        voxel_color = voxel_types[int(voxel_type) - 1]
        return (tuple(processed_face), voxel_color)

    def checkVisibility(self, voxel_position, face_index):
        face_normal = FACE_NORMALS[face_index]

        voxel_centre = voxel_position + pg.Vector3(0.5, 0.5, 0.5)

        # Dot product of the face normal to the camera vector
        # If this is positive, they are pointing in roughly the same direction - <90 degrees
        # If it's negative, they are pointing roughly away from each other - >90 degrees
        # 3blue1brown has a wonderful linear algebra video explaining this: https://www.youtube.com/watch?v=LyGKycYT2v0
        face_to_camera = np.dot(face_normal, voxel_centre)

        # Use a slight bias to prevent shapes being culled too aggressively
        is_visible = face_to_camera <= -0.5

        return is_visible

    def project_vertex(self, vertex):
        x = ((vertex.x / vertex.z) + 1) * CENTRE[0]
        y = ((vertex.y / vertex.z) + 1) * CENTRE[1]

        return (x, y)
    
    def sortVoxels(self, mesh):
        return sorted(mesh, key=lambda position: (position[0]-camera.position).length_squared())[::-1]


pg.init()
screen = pg.display.set_mode((WIDTH, HEIGHT))
clock = pg.time.Clock()
previous_time = 0

camera = Camera((0, 0, 0), (0, 0, 0))
world = Chunk((0, 0, 0))
renderer = Renderer()

for i in range(CHUNK_SIZE):
    for j in range(CHUNK_SIZE):
            world.setVoxel((i, 0, j), randint(0, 4))


# Mouse lock
pg.mouse.set_visible(False)
pg.event.set_grab(True)

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
    voxels_mesh = world.constructMesh()

    renderer.render(voxels_mesh)

    pg.display.flip()
    #clock.tick(MAX_FPS)

pg.quit()
