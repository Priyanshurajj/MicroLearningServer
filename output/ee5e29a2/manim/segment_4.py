from manim import *

class Segment4Scene(Scene):
    def construct(self):
        # Set up the chemical equation for photosynthesis using MathTex
        # The equation is broken into logical parts for sequential animation
        equation = MathTex(
            "6CO_2",                # Part 0: Carbon Dioxide
            r"\quad + \quad",        # Part 1: Plus operator
            "6H_2O",                # Part 2: Water
            r"\quad \xrightarrow{\text{Sunlight}} \quad", # Part 3: Reaction arrow with Sunlight
            "C_6H_{12}O_6",         # Part 4: Glucose (sugar)
            r"\quad + \quad",        # Part 5: Plus operator
            "6O_2"                  # Part 6: Oxygen
        ).scale(1.2).to_center()

        # Apply vibrant colors to different parts of the equation
        # The default color is WHITE, so we only need to color the specific parts.
        equation.get_part_by_tex("CO_2").set_color(YELLOW)
        equation.get_part_by_tex("H_2O").set_color(BLUE)
        equation.get_part_by_tex("Sunlight").set_color(ORANGE)
        equation.get_part_by_tex("C_6H_{12}O_6").set_color(RED)
        equation.get_part_by_tex("O_2").set_color(GREEN)

        # Define logical groups for animation based on the narration
        carbon_dioxide = equation[0]
        water = VGroup(equation[1], equation[2])
        sunlight_arrow = equation[3]
        sugar = equation[4]
        oxygen = VGroup(equation[5], equation[6])

        # Animate the equation appearing step-by-step to match the narration
        self.wait(0.5)

        # "Carbon dioxide..."
        self.play(Write(carbon_dioxide), run_time=1.5)
        self.wait(0.5)

        # "...plus water..."
        self.play(Write(water), run_time=1.5)
        self.wait(0.5)

        # "...with sunlight..."
        self.play(Write(sunlight_arrow), run_time=1.5)
        self.wait(0.5)

        # "...creates sugar for food..."
        self.play(Write(sugar), run_time=1.5)
        self.wait(0.5)

        # "...and oxygen for us to breathe!"
        self.play(Write(oxygen), run_time=1.5)

        # Hold the final frame for the viewer
        self.wait(1)