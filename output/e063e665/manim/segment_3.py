from manim import *

class Segment3Scene(Scene):
    def construct(self):
        # Define colors as per specification
        CO2_color = BLUE_E
        H2O_color = YELLOW_E
        LightEnergy_color = ORANGE
        Arrow_color = WHITE
        Glucose_color = GREEN_E
        Oxygen_color = RED_E
        Leaf_color = DARK_GREEN
        Chloroplast_color = GREEN_A
        Plus_color = LIGHT_GRAY

        # 1. Create a simplified, stylized cross-section of a plant leaf
        leaf_boundary = RoundedRectangle(
            width=10, height=5, corner_radius=2, color=Leaf_color, fill_opacity=0.7
        )
        cell = Rectangle(
            width=3, height=2.5, color=GREEN_D, fill_opacity=0.5
        ).move_to(leaf_boundary.get_center() + LEFT * 1.5)
        
        target_chloroplast = Ellipse(
            width=0.6, height=0.4, color=Chloroplast_color, fill_opacity=1
        ).move_to(cell.get_center())
        
        other_chloroplasts = VGroup(
            target_chloroplast.copy().scale(0.8).shift(UP * 0.7 + RIGHT * 0.5),
            target_chloroplast.copy().scale(0.9).shift(DOWN * 0.7 + RIGHT * 0.2),
            target_chloroplast.copy().scale(0.7).shift(DOWN * 0.5 + LEFT * 0.8),
        )
        
        leaf_parts_to_fade = VGroup(leaf_boundary, cell, other_chloroplasts)
        leaf_cross_section = VGroup(leaf_parts_to_fade, target_chloroplast)

        self.play(Create(leaf_cross_section), run_time=1.5)
        self.wait(0.2)

        # 2. Smoothly zoom into a single chloroplast
        self.camera.frame.save_state()
        self.play(
            self.camera.frame.animate.set(width=target_chloroplast.width * 4).move_to(
                target_chloroplast
            ),
            run_time=2.0,
        )
        self.wait(0.2)

        # 3. Fade out the leaf and move the chloroplast
        self.play(
            FadeOut(leaf_parts_to_fade),
            Restore(self.camera.frame),
            target_chloroplast.animate.scale(0.5).move_to(UP * 3 + LEFT * 5),
            run_time=1.5,
        )
        self.wait(0.3)

        # 4. Animate the chemical equation for photosynthesis
        # Using \mathrm for upright chemical formulas is more standard than \text
        co2 = MathTex("6\\mathrm{CO}_2", color=CO2_color)
        plus1 = MathTex("+", color=Plus_color)
        h2o = MathTex("6\\mathrm{H}_2\\mathrm{O}", color=H2O_color)
        plus2 = MathTex("+", color=Plus_color)
        light_energy = MathTex("\\text{Light Energy}", color=LightEnergy_color)
        arrow = MathTex("\\rightarrow", color=Arrow_color)
        glucose = MathTex("\\mathrm{C}_6\\mathrm{H}_{12}\\mathrm{O}_6", color=Glucose_color)
        plus3 = MathTex("+", color=Plus_color)
        o2 = MathTex("6\\mathrm{O}_2", color=Oxygen_color)

        # Position and write each component sequentially
        co2.move_to(LEFT * 4)
        self.play(Write(co2), run_time=0.5)
        
        plus1.next_to(co2, RIGHT, buff=0.2)
        self.play(Write(plus1), run_time=0.2)
        
        h2o.next_to(plus1, RIGHT, buff=0.2)
        self.play(Write(h2o), run_time=0.5)
        
        plus2.next_to(h2o, RIGHT, buff=0.2)
        self.play(Write(plus2), run_time=0.2)
        
        light_energy.next_to(plus2, RIGHT, buff=0.2)
        self.play(Write(light_energy), run_time=0.8)
        
        reactants = VGroup(co2, plus1, h2o, plus2, light_energy)
        
        arrow.next_to(reactants, RIGHT, buff=0.4)
        self.play(Write(arrow), run_time=0.5)
        
        glucose.next_to(arrow, RIGHT, buff=0.4)
        self.play(Write(glucose), run_time=0.8)
        
        plus3.next_to(glucose, RIGHT, buff=0.2)
        self.play(Write(plus3), run_time=0.2)
        
        o2.next_to(plus3, RIGHT, buff=0.2)
        self.play(Write(o2), run_time=0.5)
        
        self.wait(0.3)

        # 5. Group, center, and scale the final equation
        equation_group = VGroup(reactants, arrow, glucose, plus3, o2)
        self.play(
            equation_group.animate.move_to(ORIGIN).scale(0.8),
            run_time=0.5
        )

        self.wait(1)