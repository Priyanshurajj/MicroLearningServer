from manim import *

class Segment3Scene(Scene):
    def construct(self):
        # Set an overall scale for the equation to ensure it fits well
        scale_factor = 1.2

        # Create the MathTex objects for each part of the equation
        # Part 1: Reactants (Carbon Dioxide + Water)
        reactants = MathTex(r"6\text{CO}_2 + 6\text{H}_2\text{O}", color=WHITE)

        # Part 2: Arrow with light energy text
        arrow_and_text = MathTex(r"\xrightarrow{\text{light energy}}")

        # Part 3: Products (Glucose + Oxygen)
        products = MathTex(r"\text{C}_6\text{H}_{12}\text{O}_6 + 6\text{O}_2", color=WHITE)

        # Group all parts and arrange them horizontally
        full_equation = VGroup(reactants, arrow_and_text, products).arrange(RIGHT, buff=0.4)
        
        # Scale and center the entire equation on the screen
        full_equation.scale(scale_factor).center()

        # Color the "light energy" text specifically to YELLOW
        # The arrow will remain the default color (WHITE)
        arrow_and_text.get_part_by_tex("light energy").set_color(YELLOW)

        # Animation sequence
        # Initial pause for pacing
        self.wait(0.5)

        # "And here's the secret recipe! Carbon dioxide plus water..."
        # Animate the appearance of the reactants
        self.play(Write(reactants, run_time=2.0))
        self.wait(1.0)

        # "...with a little help from sunlight..."
        # Animate the arrow and the "light energy" text
        self.play(Write(arrow_and_text, run_time=2.0))
        self.wait(1.0)

        # "...transforms into something amazing."
        # Animate the appearance of the products
        self.play(Write(products, run_time=2.5))

        # Hold the final frame for a moment before the scene ends
        self.wait(1)