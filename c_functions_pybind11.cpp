#include <pybind11/pybind11.h>

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

bool checkVisibility(Vector3D position, Vector3D normal) {
        // Dot product of the face normal to the camera vector
        // If this is positive, they are pointing in roughly the same direction - <90 degrees
        // If it's negative, they are pointing roughly away from each other - >90 degrees
        // 3blue1brown has a wonderful linear algebra video explaining this: https://www.youtube.com/watch?v=LyGKycYT2v0 

        float face_to_camera = 
                position.x * normal.x +
                position.y * normal.y +
                position.z * normal.z;

        // Theres a slight tolerance to prevent faces popping out of view too early
        bool is_visible = (position.x * normal.x + position.y * normal.y + position.z * normal.z) <= -0.5;

        return is_visible;
}

pybind11::tuple projectVertexWrapper(pybind11::tuple position, pybind11::tuple centre) {
        Vector3D input_position;
        input_position.x = position[0].cast<float>();
        input_position.y = position[1].cast<float>();
        input_position.z = position[1].cast<float>();

        Vector2D input_centre;
        input_centre.x = centre[0].cast<int>();
        input_centre.y = centre[1].cast<int>();

        Vector2D projected_vertex = projectVertex(input_position, input_centre);

        return pybind11::make_tuple(projected_vertex.x, projected_vertex.y);

}

bool checkVisibilityWrapper(pybind11::tuple position, pybind11::tuple normal) {
        Vector3D input_position;
        input_position.x = position[0].cast<float>();
        input_position.y = position[1].cast<float>();
        input_position.z = position[1].cast<float>();

        Vector3D input_normal;
        input_normal.x = normal[0].cast<float>();
        input_normal.y = normal[1].cast<float>();
        input_normal.z = normal[1].cast<float>();

        bool is_visible = checkVisibility(input_position, input_normal);
        return is_visible;
}

PYBIND11_MODULE(c_functions, file) {
        file.def("projectVertex", &projectVertexWrapper);
        file.def("checkVisibility", &checkVisibilityWrapper);
}


int main() {}