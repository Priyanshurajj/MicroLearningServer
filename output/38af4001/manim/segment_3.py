from manim import *

class Segment3Scene(Scene):
    def construct(self):
        # Target duration: ~9.0 seconds

        # Define colors from the specification
        CO2_COLOR = GREY_B
        WATER_COLOR = BLUE
        SUN_COLOR = YELLOW
        GLUCOSE_COLOR = GREEN_SCREEN
        OXYGEN_COLOR = BLUE_D
        CHLOROPHYLL_COLOR = GREEN
        PLUS_ARROW_COLOR = WHITE

        # --- Part 1: Ingredient Icons ---
        # Create icons as specified in the visual description
        icon_co2 = Tex('CO$_2$').scale(1.5).set_color(CO2_COLOR).shift(LEFT * 3)
        icon_water = Tex('H$_2$O').scale(1.5).set_color(WATER_COLOR) # at ORIGIN
        icon_sun = Tex('Sunlight').scale(1.5).set_color(SUN_COLOR).shift(RIGHT * 3)
        
        # Animate icons appearing and disappearing
        self.play(
            FadeIn(icon_co2, shift=DOWN),
            FadeIn(icon_water, shift=DOWN),
            FadeIn(icon_sun, shift=DOWN),
            run_time=1.0
        )
        self.wait(1.2) # Adjusted for timing
        self.play(
            FadeOut(icon_co2, shift=UP),
            FadeOut(icon_water, shift=UP),
            FadeOut(icon_sun, shift=UP),
            run_time=1.0
        )
        self.wait(0.3) # Adjusted for timing

        # --- Part 2: Chemical Equation ---
        # Create equation elements as specified
        co2_term = MathTex('6CO_2').set_color_by_tex('CO_2', CO2_COLOR)
        plus1 = MathTex('+').set_color(PLUS_ARROW_COLOR)
        h2o_term = MathTex('6H_2O').set_color_by_tex('H_2O', WATER_COLOR)
        plus2 = MathTex('+').set_color(PLUS_ARROW_COLOR)
        light_term = MathTex('\\text{Light Energy}').set_color(SUN_COLOR)
        arrow = MathTex('\\rightarrow').set_color(PLUS_ARROW_COLOR)
        glucose_term = MathTex('C_6H_{12}O_6').set_color(GLUCOSE_COLOR)
        plus3 = MathTex('+').set_color(PLUS_ARROW_COLOR)
        oxygen_term = MathTex('6O_2').set_color_by_tex('O_2', OXYGEN_COLOR)

        # Group and arrange the full equation
        equation = VGroup(
            co2_term, plus1, h2o_term, plus2, light_term,
            arrow,
            glucose_term, plus3, oxygen_term
        ).arrange(RIGHT, buff=0.25).scale(1.1)

        # Animate the equation building up sequentially
        self.play(
            Succession(
                *[Write(part) for part in equation],
                lag_ratio=0.5
            ),
            run_time=3.0 # Adjusted for timing
        )
        self.wait(0.5)

        # --- Part 3: Chlorophyll Flash ---
        # Create the chlorophyll label
        chlorophyll_label = Tex('Chlorophyll').scale(3).set_color(CHLOROPHYLL_COLOR).set_opacity(0.4)
        chlorophyll_label.move_to(equation.get_center()).set_z_index(-1)

        # Animate the flash
        self.play(FadeIn(chlorophyll_label), run_time=0.5)
        self.play(FadeOut(chlorophyll_label), run_time=0.5)

        # Hold the final frame
        self.wait(1)