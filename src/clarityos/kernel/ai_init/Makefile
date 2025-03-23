CC = gcc
CFLAGS = -Wall -Wextra -g -O2 -pthread
LDFLAGS = -pthread

SOURCES = init_main.c process_manager.c resource_governor.c learning_engine.c model_runtime.c system_state.c system_monitor.c
OBJECTS = $(SOURCES:.c=.o)
EXECUTABLE = ai_init

.PHONY: all clean

all: $(EXECUTABLE)

$(EXECUTABLE): $(OBJECTS)
	$(CC) $(OBJECTS) -o $@ $(LDFLAGS)

%.o: %.c
	$(CC) -c $(CFLAGS) $< -o $@

clean:
	rm -f $(OBJECTS) $(EXECUTABLE)