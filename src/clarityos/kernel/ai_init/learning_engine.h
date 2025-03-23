#ifndef LEARNING_ENGINE_H
#define LEARNING_ENGINE_H

#include "process_manager.h"
#include "resource_governor.h"
#include "system_state.h"

// Tensor data structure for model input/output
typedef struct {
    float *data;
    int size;
} Tensor;

// Model handle structure
typedef struct {
    void *handle;
    char name[64];
} ModelHandle;

// Function prototypes
void init_learning_engine();
ProcessGroup *generate_optimal_sequence(SystemState state);
ResourcePolicy generate_resource_policy(SystemState state);
ProcessAdjustments *get_process_adjustments(SystemState state);
void update_models();
void init_learning_storage();

// Model runtime functions (implemented in model_runtime.c)
void init_model_runtime();
ModelHandle *load_model(const char *model_path);
Tensor *run_model_inference(ModelHandle *model, Tensor *input);

// Tensor creation and conversion functions
Tensor *create_system_state_tensor(SystemState state);
ProcessGroup *tensor_to_process_groups(Tensor *tensor);
ResourcePolicy tensor_to_resource_policy(Tensor *tensor);
ProcessAdjustments *tensor_to_process_adjustments(Tensor *tensor);

// Memory management functions
void free_tensor(Tensor *tensor);
void free_process_adjustments(ProcessAdjustments *adjustments);

#endif /* LEARNING_ENGINE_H */