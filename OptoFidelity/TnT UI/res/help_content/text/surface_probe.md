## Surface probing

Surface probing is a procedure where the robot moves down in steps until it hits a rigid surface. The surface detection
is usually based on detecting voice coil movement.

Surface probing is useful for determining surface positions when e.g. positioning DUT corner locations.

Once probing is started, it is possible to abort it by pressing the "Abort" button. The probing will not stop instantaneously
but instead within one probing step.

Caution: Make sure that when robot moves down from current location, the tip is the first thing that will become in
contact with a surface. Otherwise surface contact is not detected and the result is a collision that can cause
damage to the system.

![Surface probing.](ui_help_images/surface_probing.jpg "Surface probing.")

The above image illustrates a successful probing of DUT surface. The starting position is above the DUT and
there are no obstacles when the tip is moved down on the DUT surface.

The image below illustrates incorrect probing start configuration. The black cover box would collide with the
elevated table before the tip would become contact with any surface. 

![Risk of collision in surface probing.](ui_help_images/probing_incorrect.jpg "Risk of collision in surface probing.")