from manim import *

class Segment4Scene(Scene):
    def construct(self):
        # Create the full chemical equation for photosynthesis using MathTex
        # The equation is broken into parts to allow for individual coloring and animation
        equation = MathTex(
            "6CO_2",       # Part 0
            "+",           # Part 1
            "6H_2O",       # Part 2
            "+",           # Part 3
            r"\text{Sunlight}", # Part 4
            r"\rightarrow",    # Part 5
            "C_6H_{12}O_6",# Part 6
            "+",           # Part 7
            "6O_2"         # Part 8
        ).scale(1.2)

        # Apply the specified vibrant color scheme to the equation parts
        equation.set_color_by_tex("6CO_2", WHITE)
        equation.set_color_by_tex("6H_2O", BLUE)
        equation.set_color_by_tex("Sunlight", YELLOW)
        equation.set_color_by_tex(r"\rightarrow", WHITE)
        equation.set_color_by_tex("C_6H_{12}O_6", GREEN_B)
        equation.set_color_by_tex("6O_2", RED_A)

        # Group the equation components for sequential animation
        reactants = VGroup(equation[0:5])
        arrow = VGroup(equation[5])
        products = VGroup(equation[6:])

        # Animate the appearance of the reactants (simple ingredients)
        self.play(Write(reactants), run_time=2.5)
        self.wait(1)

        # Animate the appearance of the reaction arrow
        self.play(Create(arrow), run_time=1.5)
        self.wait(1)

        # Animate the transformation from reactants to products, showing the chemical change
        # TransformFromCopy creates a visual link from the ingredients to the results
        self.play(
            TransformFromCopy(reactants, products),
            run_time=3
        )

        # Hold the final frame to show the complete equation
        self.wait(1)