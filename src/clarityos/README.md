# ClarityOS - AI-Native Operating System

ClarityOS is an ambitious project to create a true AI-native operating system where AI is not just an application or service but the fundamental organizing principle of the entire system. The AI doesn't just run on the OS; the AI *is* the OS.

## Core Vision

ClarityOS reimagines the operating system with these foundational principles:

- **AI as the OS**: The AI is the fundamental organizing principle, not just an add-on
- **Intent-Based Computing**: Users express intent rather than commands, and the AI determines how to fulfill it
- **Adaptive Resource Management**: System resources are allocated dynamically based on learning rather than static policies
- **Contextual Understanding**: The system understands the user's context and adapts accordingly
- **Self-Evolution**: The OS improves itself over time through learning from system and user behaviors

## Directory Structure

- `__init__.py` - Package initialization
- `main.py` - Current main entry point for ClarityOS
- `core/` - Core system components
  - `message_bus.py` - Central communication system
  - `agent_manager.py` - Agent lifecycle management
- `agents/` - AI agent implementations
  - `resource_agent.py` - Resource allocation agent
  - `intent_agent.py` - Natural language understanding agent
- `kernel/` - Lower-level OS components
  - `ai_init/` - AI-driven init system (replacement for systemd/sysvinit)
  - `ai_sched/` - AI-driven scheduler (future)
  - `ai_mem/` - AI-driven memory manager (future)
- `docs/` - Documentation
  - `architecture/` - Architectural specifications
  - `AI-OS-VISION.md` - Vision document for true AI-native OS
  - `AI-OS-ROADMAP.md` - Implementation roadmap
- `boot_options/` - Scripts for different boot mechanisms

## Key Components

### AI Init System

The AI Init System is a fundamental shift from traditional init systems:

- **Process Lifecycle Management**: Intelligently starts, stops, and manages processes based on learned patterns and current needs
- **Resource Governance**: Allocates resources based on learned importance rather than static priorities
- **Adaptive Optimization**: Continuously improves boot and runtime performance through learning

### AI Shell

The AI Shell replaces traditional command shells with:

- **Natural Language Understanding**: Control the system through natural language rather than command syntax
- **Intent Resolution**: Determine user intent and map to appropriate system operations
- **Contextual Awareness**: Understand commands in the context of user history and system state

### AI Kernel Integration

Future kernel integration will include:

- **AI Scheduler**: Replace the traditional completely fair scheduler (CFS) with an AI-driven scheduler that prioritizes based on learned patterns
- **AI Memory Manager**: Implement predictive paging and intelligent swapping based on usage patterns
- **AI I/O Subsystem**: Optimize I/O operations based on learned access patterns

## Architecture

This diagram illustrates the ClarityOS architecture as a true AI-native OS:

```
┌───────────────────────────────────────────────────┐
│                System Hardware                    │
└───────────────┬───────────────────────────────────┘
                │
┌───────────────▼───────────────────────────────────┐
│              AI Kernel Layer                      │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐      │
│  │ AI        │  │ AI Memory │  │ AI I/O    │      │
│  │ Scheduler │  │ Manager   │  │ Subsystem │      │
│  └───────────┘  └───────────┘  └───────────┘      │
└───────────────┬───────────────────────────────────┘
                │
┌───────────────▼───────────────────────────────────┐
│              AI Init System                       │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐      │
│  │ Process   │  │ Resource  │  │Dependency │      │
│  │ Lifecycle │  │ Governor  │  │ Resolver  │      │
│  └───────────┘  └───────────┘  └───────────┘      │
└───────────────┬───────────────────────────────────┘
                │
┌───────────────▼───────────────────────────────────┐
│           System & User Services                  │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐      │
│  │ File      │  │ Network   │  │ Security  │      │
│  │ System    │  │ Stack     │  │ Services  │      │
│  └───────────┘  └───────────┘  └───────────┘      │
└───────────────┬───────────────────────────────────┘
                │
┌───────────────▼───────────────────────────────────┐
│              Message Bus                          │
└───────────────┬───────────────────────────────────┘
                │
┌───────────────▼───────────────────────────────────┐
│              User Interface Layer                 │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐      │
│  │ AI        │  │ Adaptive  │  │ Intent    │      │
│  │ Shell     │  │ GUI       │  │ Resolver  │      │
│  └───────────┘  └───────────┘  └───────────┘      │
└───────────────┬───────────────────────────────────┘
                │
┌───────────────▼───────────────────────────────────┐
│              Applications                         │
└───────────────────────────────────────────────────┘
```

## Implementation Roadmap

ClarityOS is being developed in phases:

1. **Foundation Phase** (Current)
   - Message bus architecture
   - Agent system framework
   - Boot options for various platforms

2. **AI Core Phase** (In Progress)
   - AI Init System implementation
   - AI Shell development
   - System monitoring and learning framework

3. **Kernel Integration Phase** (Planned)
   - AI scheduler modules
   - Memory management subsystem
   - I/O prioritization system

4. **Complete AI OS Phase** (Future)
   - Full system integration
   - Learning algorithms across the stack
   - Developer APIs for AI-native applications

For more details, see the [AI-OS-ROADMAP.md](docs/AI-OS-ROADMAP.md) document.

## Contributing

Contributions are welcome! See the [Skynet Project README](../../README.md) for general contribution guidelines.

For ClarityOS specific contributions:

1. Focus on the AI-native OS components described in the vision document
2. Work on the components identified in the roadmap
3. Improve the AI decision-making capabilities
4. Enhance the integration between the AI and kernel/system components

See the [AI-OS-VISION.md](docs/AI-OS-VISION.md) document for more details on the project vision.

### Running ClarityOS

To start the ClarityOS core manually:

```bash
# From the project root directory
python -m src.clarityos.main
```

### Boot Options

ClarityOS can be configured to start automatically at system boot using several methods:

#### Windows Options

1. **Windows Service** - Run as a system service (recommended for production)
   ```powershell
   # Run as administrator
   cd src/clarityos/boot_options
   ./windows_service.ps1
   ```

2. **Windows Autostart** - Start when user logs in
   ```powershell
   cd src/clarityos/boot_options
   ./windows_autostart.ps1
   ```

#### Linux Options

1. **SystemD Service** - Run as a system service (recommended for production)
   ```bash
   cd src/clarityos/boot_options
   chmod +x linux_systemd.sh
   ./linux_systemd.sh
   ```

2. **User Autostart** - Start when user logs in
   ```bash
   cd src/clarityos/boot_options
   chmod +x linux_user_autostart.sh
   ./linux_user_autostart.sh
   ```

#### Docker Deployment

Run ClarityOS in a containerized environment (cross-platform):
```bash
cd src/clarityos/boot_options
chmod +x docker_setup.sh
./docker_setup.sh
```