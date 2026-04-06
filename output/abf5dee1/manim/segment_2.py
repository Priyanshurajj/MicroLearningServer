from manim import *

class Segment2Scene(Scene):
    def construct(self):
        # A stylized green plant stands centered.
        stem = Line(DOWN * 1.5, UP * 0.5, color=GREEN_E, stroke_width=12)
        leaf_shape = Polygon(
            stem.get_center() + LEFT * 0.1,
            stem.get_center() + UP * 1.0 + RIGHT * 0.6,
            stem.get_center() + RIGHT * 0.9,
            color=GREEN_E,
            fill_opacity=1.0,
            stroke_width=0
        )
        leaf1 = leaf_shape.rotate(-PI / 12, about_point=stem.get_center())
        leaf2 = leaf1.copy().scale(-1, about_point=stem.get_center())
        plant = VGroup(stem, leaf1, leaf2).move_to(ORIGIN).shift(DOWN * 0.5)

        # A bright yellow sun model is positioned in the upper left.
        sun_core = Circle(radius=0.5, color=YELLOW, fill_opacity=1.0)
        sun_rays = VGroup(*[
            Line(ORIGIN, 0.7 * RIGHT, color=YELLOW, stroke_width=3).rotate(angle, about_point=ORIGIN)
            for angle in np.arange(0, TAU, TAU / 10)
        ])
        sun = VGroup(sun_core, sun_rays).to_corner(UL, buff=0.5)

        # Animate creation of plant and sun
        self.play(Create(plant), run_time=1.0)
        self.play(FadeIn(sun, scale=0.5), run_time=1.0)
        self.wait(0.2)

        # Energy particles (small yellow dots) emanate from the sun and flow into the plant
        particle_animations = []
        for _ in range(20):
            dot = Dot(sun.get_center(), color=YELLOW, radius=0.05)
            # Animate particle creation, movement along an arc, and disappearance
            anim = Succession(
                FadeIn(dot, scale=0.5),
                dot.animate(path_arc=-PI / 8).move_to(plant.get_center()),
                FadeOut(dot, scale=0.5)
            )
            particle_animations.append(anim)

        # The plant subtly glows as it absorbs energy
        glow_animation = plant.animate.set_fill(GREEN_A, opacity=0.8).set_stroke(color=GREEN_E, width=2)

        self.play(
            LaggedStart(*particle_animations, lag_ratio=0.1),
            glow_animation,
            run_time=2.5
        )
        self.wait(0.3)

        # Below, the equation for energy transformation appears.
        equation = MathTex(r"\text{Light Energy} \rightarrow \text{Chemical Energy}", color=WHITE)
        equation.next_to(plant, DOWN, buff=1.2)
        
        self.play(Write(equation), run_time=1.5)

        # Hold the final frame
        self.wait(1)