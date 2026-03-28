from manim import *

class Segment3Scene(Scene):
    def construct(self):
        # As per the specification, a stylized chlorophyll molecule is represented by text.
        # This appears briefly at the start.
        chlorophyll_molecule = Tex("Chlorophyll", color=GREEN_B, font_size=72)
        chlorophyll_molecule.move_to(ORIGIN)

        # Animation: Create the chlorophyll text.
        self.play(Create(chlorophyll_molecule), run_time=1.0)
        self.wait(1.0)  # Delay after creation

        # Animation: Fade out the chlorophyll text to make way for the equation.
        self.play(FadeOut(chlorophyll_molecule), run_time=0.5)
        self.wait(0.5)  # Delay after fade out

        # Define the components of the photosynthesis chemical equation.
        # Colors are based on the provided color scheme.
        co2_term = MathTex("6CO_2", color=BLUE_D)
        plus1 = MathTex("+", color=WHITE)
        h2o_term = MathTex("6H_2O", color=TEAL_A)
        plus2 = MathTex("+", color=WHITE)
        sunlight_term = MathTex(r"\text{Sunlight Energy}", color=YELLOW_E)
        arrow = MathTex(r"\rightarrow", color=WHITE)
        glucose_term = MathTex("C_6H_{12}O_6", color=PURPLE_B)
        plus3 = MathTex("+", color=WHITE)
        o2_term = MathTex("6O_2", color=RED_C)

        # Group all parts of the equation to arrange them easily.
        equation = VGroup(
            co2_term, plus1, h2o_term, plus2, sunlight_term,
            arrow,
            glucose_term, plus3, o2_term
        )
        
        # Arrange the equation parts horizontally and center them on the screen.
        equation.arrange(RIGHT, buff=0.25).scale(0.9).move_to(ORIGIN)

        # Animate the equation appearing piece by piece using a Succession animation.
        self.play(
            Succession(
                Write(co2_term, run_time=0.7),
                Write(plus1, run_time=0.3),
                Write(h2o_term, run_time=0.7),
                Write(plus2, run_time=0.3),
                Write(sunlight_term, run_time=1.0),
                Write(arrow, run_time=0.6),
                Write(glucose_term, run_time=1.0),
                Write(plus3, run_time=0.3),
                Write(o2_term, run_time=0.7),
            )
        )

        # Hold the final frame for a moment before the scene ends.
        self.wait(1)