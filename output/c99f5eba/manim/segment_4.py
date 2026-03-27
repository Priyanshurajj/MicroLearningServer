from manim import *

class Segment4Scene(Scene):
    def construct(self):
        # Set up the chemical equation using MathTex for proper formatting.
        # We define each part as a separate string to animate them individually.
        equation = MathTex(
            r"6CO_2",        # Part 1: Carbon Dioxide
            r"+ 6H_2O",      # Part 2: Water
            r"\rightarrow",  # Part 3: Reaction arrow
            r"C_6H_{12}O_6", # Part 4: Glucose
            r"+ 6O_2",       # Part 5: Oxygen
            font_size=72
        ).center()

        # Assign parts to variables for clarity and easier manipulation
        part1 = equation.get_part_by_tex("6CO_2")
        part2 = equation.get_part_by_tex("+ 6H_2O")
        part3 = equation.get_part_by_tex(r"\rightarrow")
        part4 = equation.get_part_by_tex("C_6H_{12}O_6")
        part5 = equation.get_part_by_tex("+ 6O_2")

        # Set vibrant colors for each component of the equation
        part1.set_color(BLUE)
        part2.set_color(YELLOW)
        part3.set_color(WHITE)
        part4.set_color(GREEN)
        part5.set_color(RED)

        # Animate the equation appearing piece by piece
        self.wait(0.5)

        # Animate 6CO2
        self.play(Write(part1, run_time=1.0))
        self.play(Flash(part1, color=WHITE, flash_radius=0.6, run_time=0.5))
        self.wait(0.25)

        # Animate + 6H2O
        self.play(Write(part2, run_time=1.0))
        self.play(Flash(part2, color=WHITE, flash_radius=0.8, run_time=0.5))
        self.wait(0.25)

        # Animate the reaction arrow
        self.play(Write(part3, run_time=0.75))
        self.wait(0.25)

        # Animate C6H12O6
        self.play(Write(part4, run_time=1.5))
        self.play(Flash(part4, color=WHITE, flash_radius=1.2, run_time=0.5))
        self.wait(0.25)

        # Animate + 6O2
        self.play(Write(part5, run_time=1.0))
        self.play(Flash(part5, color=WHITE, flash_radius=0.8, run_time=0.5))

        # Hold the final frame for a moment
        self.wait(1)