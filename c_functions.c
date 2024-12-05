#include <stdio.h>  // Input/Output
#include <stdbool.h>   // Booleans

// Structure to store the projected vertex
// TODO custom vector class
typedef struct {
        int x;
        int y;
} Vector2D;

typedef struct {
        float x;
        float y;
        float z;
} Vector3D;

Vector2D projectVertex(Vector3D position, Vector2D centre) {
        int projected_x = ((position.x / position.z) + 1) * centre.x;
        int projected_y = ((position.y / position.z) + 1) * centre.y;

        return (Vector2D){projected_x, projected_y};
}

bool checkVisibility(Vector3D voxel, Vector3D normal) {
        // Dot product of the face normal to the camera vector
        // If this is positive, they are pointing in roughly the same direction - <90 degrees
        // If it's negative, they are pointing roughly away from each other - >90 degrees
        // 3blue1brown has a wonderful linear algebra video explaining this: https://www.youtube.com/watch?v=LyGKycYT2v0 

        float face_to_camera = 
                voxel.x * normal.x +
                voxel.y * normal.y +
                voxel.z * normal.z;

        // Theres a slight tolerance to prevent faces popping out of view too early
        bool is_visible = (voxel.x * normal.x + voxel.y * normal.y + voxel.z * normal.z) <= -0.5;

        return is_visible;
}