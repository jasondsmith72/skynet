use vectormatrix::{Matrix, Vector};

/// A simple dense layer for a neural network.
pub struct DenseLayer<const IN: usize, const OUT: usize> {
    weights: Matrix<f32, OUT, IN>,
    biases: Vector<f32, OUT>,
}

impl<const IN: usize, const OUT: usize> DenseLayer<IN, OUT> {
    /// Creates a new dense layer with the given weights and biases.
    pub fn new(weights_rows: [Vector<f32, IN>; OUT], biases: [f32; OUT]) -> Self {
        Self {
            weights: Matrix::new_rows(weights_rows),
            biases: Vector::new(biases),
        }
    }

    /// Performs the forward pass for this layer.
    pub fn forward(&self, inputs: &Vector<f32, IN>) -> Vector<f32, OUT> {
        let output_matrix = self.weights * *inputs;
        let output_vector = output_matrix.columns()[0];
        output_vector + self.biases
    }
}

/// A simple ReLU activation function.
pub fn relu<const D: usize>(vector: &mut Vector<f32, D>) {
    for i in 0..D {
        if vector[i] < 0.0 {
            vector[i] = 0.0;
        }
    }
}

/// Helper function to print a vector to the serial console.
pub fn print_vector<const D: usize>(vector: &Vector<f32, D>, name: &str) {
    serial_println!("{}:", name);
    serial_print!("[ ");
    for i in 0..D {
        // We still need to cast to i32 for printing, as f32 support is not available.
        serial_print!("{} ", vector[i] as i32);
    }
    serial_println!("]");
}