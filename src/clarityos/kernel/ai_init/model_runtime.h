#ifndef MODEL_RUNTIME_H
#define MODEL_RUNTIME_H

#include "learning_engine.h"

// Function prototypes
void init_model_runtime();
ModelHandle *load_model(const char *model_path);
Tensor *run_model_inference(ModelHandle *model, Tensor *input);
void unload_model(ModelHandle *model);

#endif /* MODEL_RUNTIME_H */