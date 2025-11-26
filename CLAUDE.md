# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TESPy (Thermal Engineering Systems in Python) is a simulation framework for thermal engineering systems including power plants, heat pumps, and refrigeration machines. It's part of the Open Energy Modelling Framework (oemof).

## Development Commands

### Testing
- Run all tests: `pytest --cov --cov-report=term-missing -vv`
- Run specific test file: `pytest tests/test_file.py -vv`
- Run tests for specific Python version: `tox -e py310` (or py311, py312)
- Run tests ignoring src: `pytest -vv --ignore=src`

### Code Quality
- Check imports and formatting: `tox -e check`
- Check import sorting: `isort --verbose --check-only --diff src tests`
- Fix import sorting: `isort src tests`
- Check manifest: `check-manifest .`

### Documentation
- Build docs: `tox -e docs`
- Build docs manually: `sphinx-build -E -b html docs docs/_build`
- Check doc links: `sphinx-build -b linkcheck docs docs/_build`

### Running All Checks
- Run all environments: `tox`
- Run specific environments: `tox -e check,docs,py312`

## Architecture

### Core Components

1. **Network (`src/tespy/networks/network.py`)**
   - Central container for TESPy simulations
   - Creates and solves system of equations
   - Manages topology and parametrization

2. **Components (`src/tespy/components/`)**
   - Base class: `component.py` - all components inherit from Component
   - Component types organized by category:
     - `basics/` - sinks, sources, subsystem interfaces
     - `combustion/` - combustion chambers, engines
     - `heat_exchangers/` - various heat exchanger types
     - `nodes/` - mixers, splitters, separators
     - `piping/` - pipes, valves
     - `power/` - buses, generators, motors
     - `reactors/` - fuel cells, electrolyzers
     - `turbomachinery/` - turbines, compressors, pumps

3. **Connections (`src/tespy/connections/`)**
   - `connection.py` - represents fluid connections between components
   - `bus.py` - power/heat bus connections
   - Handle fluid properties, mass flow, pressure, temperature, enthalpy

4. **Tools (`src/tespy/tools/`)**
   - `fluid_properties/` - thermodynamic property calculations using CoolProp, IAPWS, PyroMat
   - `characteristics.py` - component characteristic curves
   - `data_containers.py` - data structure definitions
   - `helpers.py` - utility functions
   - `analyses.py` - exergy and entropy analysis

### Key Concepts

- **Components** are connected via **Connections** that carry fluid streams
- **Networks** contain all components and connections, solve the system
- **Fluid properties** calculated using multiple backends (CoolProp, IAPWS, PyroMat)
- **Characteristics** define component behavior at off-design conditions
- **Buses** handle power/heat transfer between components

## Project Structure

- `src/tespy/` - main source code
- `tests/` - pytest test suite with comprehensive coverage
- `tutorial/` - example scripts demonstrating TESPy usage
- `docs/` - Sphinx documentation source
- `pyproject.toml` - project configuration, dependencies, test settings

## Development Notes

- Python 3.10+ required
- Uses pytest for testing with coverage reporting
- Code style enforced via isort for import sorting
- Documentation built with Sphinx
- Supports multiple fluid property backends
- Component registry pattern for extensibility
- Extensive use of data containers for type safety
