# Module 34: Virtual data center visualization

Module 34 adds an infrastructure map to the live simulation dashboard. Virtual machines are grouped into visual racks of four and display their current status, capacity, active task, queue length, and utilization.

The visualization uses the existing real-time simulation state, so it follows running, paused, stopped, and completed simulations without changing scheduler behavior.

Rack grouping is presentational only. The scheduling algorithms remain unaware of racks and continue to use the existing virtual machine model.
