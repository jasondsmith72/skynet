#![no_std]
#![no_main]

use core::panic::PanicInfo;
use core::alloc::{GlobalAlloc, Layout};
use bootloader::{BootInfo, entry_point};
use vectormatrix::Vector;

#[macro_use]
mod serial;
mod vga_buffer;
mod memory;
mod llm;

#[global_allocator]
static ALLOCATOR: DummyAllocator = DummyAllocator;

pub struct DummyAllocator;

unsafe impl GlobalAlloc for DummyAllocator {
    unsafe fn alloc(&self, _layout: Layout) -> *mut u8 {
        panic!("no allocator")
    }

    unsafe fn dealloc(&self, _ptr: *mut u8, _layout: Layout) {
        panic!("no allocator")
    }
}

entry_point!(kernel_main);

fn kernel_main(_boot_info: &'static BootInfo) -> ! {
    serial_println!("Hello from ClarityOS Kernel!");

    // Define a simple 2-layer neural network.
    let layer1 = llm::DenseLayer::new(
        [
            Vector::new([0.1, 0.2]),
            Vector::new([0.3, 0.4]),
            Vector::new([0.5, 0.6]),
        ], // 3x2 weights
        [0.1, 0.2, 0.3], // 3-element bias vector
    );
    let layer2 = llm::DenseLayer::new(
        [Vector::new([0.7, 0.8, 0.9])], // 1x3 weights
        [0.4],                          // 1-element bias vector
    );

    // Create some sample input.
    let inputs = Vector::new([1.0, 2.0]);
    llm::print_vector(&inputs, "Input");

    // Perform the forward pass.
    let mut output1 = layer1.forward(&inputs);
    llm::print_vector(&output1, "Layer 1 Output (before ReLU)");
    llm::relu(&mut output1);
    llm::print_vector(&output1, "Layer 1 Output (after ReLU)");

    let final_output = layer2.forward(&output1);
    llm::print_vector(&final_output, "Final Output");

    serial_println!("LLM test complete.");

    loop {}
}

/// This function is called on panic.
#[panic_handler]
fn panic(info: &PanicInfo) -> ! {
    serial_println!("[PANIC] {}", info);
    loop {}
}