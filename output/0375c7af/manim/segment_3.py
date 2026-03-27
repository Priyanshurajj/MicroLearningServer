from manim import *

class Segment3Scene(Scene):
    def construct(self):
        # Set up a subtle dark green background
        self.camera.background_color = '#224422'

        # Create MathTex objects for the chemical equation
        co2_formula = MathTex("6CO_2", color=BLUE_C)
        plus1 = MathTex("+", color=WHITE)
        h2o_formula = MathTex("6H_2O", color=GREEN_C)
        
        # Use tex_to_color_map for robustly coloring parts of the MathTex object
        arrow_light_energy = MathTex(
            "\\xrightarrow{\\text{Light Energy}}",
            color=WHITE,
            tex_to_color_map={"Light Energy": YELLOW_A}
        )
        
        glucose_formula = MathTex("C_6H_{12}O_6", color=GOLD_A)
        plus2 = MathTex("+", color=WHITE)
        o2_formula = MathTex("6O_2", color=RED_C)

        # Group and arrange the equation components
        # This modifies the mobjects in-place, so they will be animated in their final positions.
        equation = VGroup(
            co2_formula, plus1, h2o_formula, arrow_light_energy, 
            glucose_formula, plus2, o2_formula
        ).arrange(RIGHT, buff=0.25).scale(1.2)

        # --- ANIMATION SEQUENCE ---

        # Animate the equation appearing sequentially
        # Narration: Here's the secret recipe in science language!
        self.play(Write(co2_formula), run_time=0.5)
        self.play(Write(plus1), run_time=0.2)
        self.play(Write(h2o_formula), run_time=0.5)
        self.play(Write(arrow_light_energy), run_time=0.8)
        self.play(Write(glucose_formula), run_time=0.8)
        self.play(Write(plus2), run_time=0.2)
        self.play(Write(o2_formula), run_time=0.5)
        
        self.wait(0.5)

        # Highlight each component as it's narrated
        # Narration: Carbon dioxide...
        self.play(
            Flash(co2_formula, color=YELLOW, flash_radius=0.6, run_time=0.8)
        )
        # Narration: ...plus water...
        self.play(
            Flash(h2o_formula, color=YELLOW, flash_radius=0.6, run_time=0.8)
        )
        # Narration: ...with a little help from sunlight...
        # get_part_by_tex works correctly because tex_to_color_map isolates the substring
        light_energy_text = arrow_light_energy.get_part_by_tex("Light Energy")
        self.play(
            Flash(light_energy_text, color=YELLOW, flash_radius=0.8, run_time=1.0)
        )
        # Narration: ...creates glucose (their food)...
        self.play(
            Flash(glucose_formula, color=YELLOW, flash_radius=0.8, run_time=0.8)
        )
        # Narration: ...and oxygen.
        self.play(
            Flash(o2_formula, color=YELLOW, flash_radius=0.6, run_time=0.8)
        )

        # Hold the final frame
        self.wait(1)