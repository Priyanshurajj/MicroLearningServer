from manim import *

class Segment3Scene(Scene):
    def construct(self):
        # Helper function to create a CO2 molecule
        def create_co2():
            carbon = Dot(color=BLACK, radius=0.1).set_stroke(color=GRAY, width=1)
            oxygen1 = Dot(color=RED, radius=0.08).move_to(carbon.get_center() + LEFT * 0.2)
            oxygen2 = Dot(color=RED, radius=0.08).move_to(carbon.get_center() + RIGHT * 0.2)
            return VGroup(carbon, oxygen1, oxygen2)

        # Helper function to create an H2O molecule
        def create_h2o():
            oxygen = Dot(color=BLUE, radius=0.1)
            hydrogen1 = Dot(color=WHITE, radius=0.06).move_to(oxygen.get_center() + 0.2 * (UP * 0.6 - LEFT * 0.8))
            hydrogen2 = Dot(color=WHITE, radius=0.06).move_to(oxygen.get_center() + 0.2 * (UP * 0.6 + RIGHT * 0.8))
            return VGroup(oxygen, hydrogen1, hydrogen2)

        # --- SCENE SETUP ---
        # Stylized leaf
        leaf = Polygon(
            [-2, 0, 0], [-1, 1.5, 0], [0, 0.5, 0], [1, 1.5, 0], [2, 0, 0], [0, -2.5, 0],
            [-2, 0, 0],
            color=GREEN_E,
            fill_opacity=0.8
        ).scale(0.9).shift(LEFT * 2.5)
        leaf.set_stroke(color=GREEN_D, width=3)

        # Stylized roots
        roots = VGroup(
            Line(leaf.get_bottom() + DOWN * 0.1, leaf.get_bottom() + DOWN * 1.5 + LEFT * 0.5, color=BROWN),
            Line(leaf.get_bottom() + DOWN * 0.1, leaf.get_bottom() + DOWN * 1.2 + RIGHT * 0.5, color=BROWN),
            Line(leaf.get_bottom() + DOWN * 0.8, leaf.get_bottom() + DOWN * 2.0, color=BROWN)
        ).set_stroke(width=4)

        # --- ANIMATION ---

        # Show leaf and roots
        self.play(FadeIn(leaf), Create(roots), run_time=1.0)

        # Narration: "They grab carbon dioxide from the air... and soak up sunlight..."
        co2_molecules = VGroup(*[create_co2().shift(RIGHT * 5 + UP * (i - 1) * 1.2) for i in range(3)])
        co2_label = MathTex("CO_2", color=WHITE).scale(1.2).to_edge(RIGHT, buff=1.5)
        sun_rays = VGroup(*[
            Line(start=UP * 4 + RIGHT * 5, end=leaf.get_center() + UR*0.5, color=YELLOW, stroke_width=3)
            .rotate(angle=(i - 2) * 0.08, about_point=UP * 4 + RIGHT * 5)
            for i in range(5)
        ])

        self.play(
            Create(sun_rays),
            FadeIn(co2_molecules, shift=RIGHT),
            run_time=1.2
        )
        self.play(
            Write(co2_label),
            co2_molecules.animate.move_to(leaf.get_center() + RIGHT),
            run_time=1.0
        )

        # Narration: "...water from the ground..."
        h2o_molecules = VGroup(*[create_h2o().shift(DOWN * 3.5 + LEFT * (i - 1) * 1.5) for i in range(3)])
        h2o_label = MathTex("H_2O", color=BLUE).scale(1.2).move_to(co2_label)

        self.play(
            FadeIn(h2o_molecules, shift=DOWN),
            run_time=0.8
        )
        self.play(
            ReplacementTransform(co2_label, h2o_label),
            h2o_molecules.animate.move_to(leaf.get_bottom() + UP * 0.5),
            run_time=1.0
        )
        self.wait(0.5)

        # Narration: "...all thanks to a special green pigment called chlorophyll."
        # Create a stylized chlorophyll molecule for the transformation
        chlorophyll_ring = Square(color=GREEN_B, fill_opacity=0.6).scale(0.8)
        mg_atom = Dot(color=WHITE, radius=0.1).move_to(chlorophyll_ring.get_center())
        side_groups = VGroup(
            Rectangle(height=0.4, width=0.2, color=GREEN_C, fill_opacity=0.8).next_to(chlorophyll_ring, UP, buff=0),
            Rectangle(height=0.4, width=0.2, color=GREEN_C, fill_opacity=0.8).next_to(chlorophyll_ring, DOWN, buff=0),
            Rectangle(height=0.2, width=0.4, color=GREEN_C, fill_opacity=0.8).next_to(chlorophyll_ring, LEFT, buff=0),
            Rectangle(height=0.2, width=0.4, color=GREEN_C, fill_opacity=0.8).next_to(chlorophyll_ring, RIGHT, buff=0),
        )
        tail = Polyline(
            [0, 0, 0], [-0.5, -0.5, 0], [-0.2, -1, 0], [-0.8, -1.5, 0],
            color=GREEN_D, stroke_width=8
        ).next_to(chlorophyll_ring, DOWN, buff=0).shift(LEFT * 0.2)
        chlorophyll_molecule = VGroup(chlorophyll_ring, mg_atom, side_groups, tail).scale(1.8).move_to(ORIGIN)

        # Fade out inputs and transform leaf
        self.play(
            FadeOut(co2_molecules, h2o_molecules, sun_rays, h2o_label, roots),
            run_time=0.8
        )
        self.play(Transform(leaf, chlorophyll_molecule), run_time=1.5)

        self.wait(1)