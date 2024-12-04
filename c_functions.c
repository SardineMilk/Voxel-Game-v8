#include <stdio.h>  // Input/Output
#include <stdbool.h>   // Booleans

// Structure to store the projected vertex
typedef struct {
        int x;
        int y;
} Vector2D;


Vector2D projectVertex(float x, float y, float z, int width, int height) {
        int projected_x = ((x / z) + 1) * width;
        int projected_y = ((y / z) + 1) * height;

        return (Vector2D){projected_x, projected_y};
}

bool checkVisibility(float voxel_x, float voxel_y, float voxel_z, int normal_x, int normal_y, int normal_z) {
        // Dot product of the face normal to the camera vector
        // If this is positive, they are pointing in roughly the same direction - <90 degrees
        // If it's negative, they are pointing roughly away from each other - >90 degrees
        // 3blue1brown has a wonderful linear algebra video explaining this: https://www.youtube.com/watch?v=LyGKycYT2v0 

        float face_to_camera = 
        voxel_x * normal_x +
        voxel_y * normal_y +
        voxel_z * normal_z;

        // Theres a slight tolerance to prevent faces popping out of view too early
        bool is_visible = face_to_camera <= -0.5;

        return is_visible;
}


void main() {}