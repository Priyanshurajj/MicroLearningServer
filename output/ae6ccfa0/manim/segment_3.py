from manim import *

class Segment3Scene(Scene):
    def construct(self):
        # This scene animates the chemical equation for photosynthesis,
        # following the narration: "It's like a magical recipe! Let's see
        # the ingredients transform into yummy plant food!"

        # Define vibrant colors for each component of the equation
        CO2_COLOR = BLUE_C
        H2O_COLOR = BLUE_C
        LIGHT_ENERGY_COLOR = YELLOW_C
        GLUCOSE_COLOR = GREEN_C
        OXYGEN_COLOR = RED_C
        OPERATOR_COLOR = WHITE

        # Create MathTex mobjects for the reactants ("ingredients")
        co2_tex = MathTex("6\\text{CO}_2", color=CO2_COLOR)
        plus1_tex = MathTex("+", color=OPERATOR_COLOR)
        h2o_tex = MathTex("6\\text{H}_2\\text{O}", color=H2O_COLOR)
        plus2_tex = MathTex("+", color=OPERATOR_COLOR)
        light_energy_tex = MathTex("\\text{Light Energy}", color=LIGHT_ENERGY_COLOR)

        # Create the reaction arrow
        arrow_tex = MathTex("\\rightarrow", color=OPERATOR_COLOR)

        # Create MathTex mobjects for the products ("yummy plant food")
        glucose_tex = MathTex("\\text{C}_6\\text{H}_{12}\\text{O}_6", color=GLUCOSE_COLOR)
        plus3_tex = MathTex("+", color=OPERATOR_COLOR)
        oxygen_tex = MathTex("6\\text{O}_2", color=OXYGEN_COLOR)

        # Group the reactants and products for easier manipulation
        reactants = VGroup(co2_tex, plus1_tex, h2o_tex, plus2_tex, light_energy_tex).arrange(RIGHT, buff=0.3)
        products = VGroup(glucose_tex, plus3_tex, oxygen_tex).arrange(RIGHT, buff=0.3)

        # Group the entire equation, arrange all parts, and scale for better visibility
        full_equation = VGroup(reactants, arrow_tex, products).arrange(RIGHT, buff=0.4)
        full_equation.scale(1.2).center()

        # --- Animation Sequence ---

        # Animate the reactants appearing, like listing ingredients for a recipe
        self.play(
            Write(reactants, run_time=3.0)
        )
        self.wait(1.0)

        # Animate the reaction arrow, signifying the transformation
        self.play(
            Write(arrow_tex, run_time=1.0)
        )
        self.wait(1.0)

        # Animate the products appearing, showing the result of the "recipe"
        self.play(
            Write(products, run_time=2.0)
        )

        # Hold the final frame to allow the viewer to read the full equation
        self.wait(1)