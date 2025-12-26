"""
Animated Background Component
=============================
Space-like particle and gradient background
"""

import flet as ft
import random
import math
from ..theme import colors


class AnimatedBackground(ft.Stack):
    """
    A stunning animated background with:
    - Deep space gradient
    - Floating particles/stars
    - Subtle aurora effect
    """
    
    def __init__(
        self,
        content: ft.Control = None,
        **kwargs,
    ):
        # Create particle layer
        particles = self._create_particles(30)
        
        # Background gradient
        gradient_bg = ft.Container(
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=[
                    "#0a0a12",
                    "#0f0a1a",
                    "#1a0a2e",
                    "#0a1a2e",
                    "#0a0a12",
                ],
                stops=[0, 0.25, 0.5, 0.75, 1],
            ),
            expand=True,
        )
        
        # Glow orbs (aurora effect)
        glow_orbs = self._create_glow_orbs()
        
        # Stack everything
        controls = [
            gradient_bg,
            glow_orbs,
            ft.Container(
                content=ft.Stack(controls=particles),
                expand=True,
            ),
        ]
        
        if content:
            controls.append(content)
        
        super().__init__(
            controls=controls,
            expand=True,
            **kwargs,
        )
    
    def _create_particles(self, count: int) -> list:
        """Create floating particle dots"""
        particles = []
        
        for i in range(count):
            # Random position and size
            size = random.uniform(1, 3)
            opacity = random.uniform(0.2, 0.6)
            
            particle = ft.Container(
                width=size,
                height=size,
                border_radius=size / 2,
                bgcolor=f"rgba(255, 255, 255, {opacity})",
                left=random.uniform(0, 100),  # Percentage
                top=random.uniform(0, 100),
                animate_opacity=ft.Animation(
                    random.randint(2000, 5000),
                    ft.AnimationCurve.EASE_IN_OUT,
                ),
            )
            particles.append(particle)
        
        return particles
    
    def _create_glow_orbs(self) -> ft.Container:
        """Create subtle aurora glow orbs"""
        return ft.Stack(
            controls=[
                # Purple glow (top-left)
                ft.Container(
                    width=400,
                    height=400,
                    border_radius=200,
                    gradient=ft.RadialGradient(
                        colors=[
                            "rgba(139, 92, 246, 0.15)",
                            "rgba(139, 92, 246, 0.05)",
                            "rgba(139, 92, 246, 0)",
                        ],
                    ),
                    left=-100,
                    top=-100,
                ),
                # Cyan glow (bottom-right)
                ft.Container(
                    width=350,
                    height=350,
                    border_radius=175,
                    gradient=ft.RadialGradient(
                        colors=[
                            "rgba(6, 182, 212, 0.12)",
                            "rgba(6, 182, 212, 0.04)",
                            "rgba(6, 182, 212, 0)",
                        ],
                    ),
                    right=-80,
                    bottom=-80,
                ),
                # Pink glow (top-right, subtle)
                ft.Container(
                    width=300,
                    height=300,
                    border_radius=150,
                    gradient=ft.RadialGradient(
                        colors=[
                            "rgba(236, 72, 153, 0.08)",
                            "rgba(236, 72, 153, 0.02)",
                            "rgba(236, 72, 153, 0)",
                        ],
                    ),
                    right=50,
                    top=100,
                ),
            ],
            expand=True,
        )


class SimpleGradientBackground(ft.Container):
    """
    A simpler gradient background without particles.
    Better performance for older devices.
    """
    
    def __init__(
        self,
        content: ft.Control = None,
        **kwargs,
    ):
        super().__init__(
            content=content,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_center,
                end=ft.alignment.bottom_center,
                colors=[
                    colors.bg_deepest,
                    "#0f0a1a",
                    colors.bg_deep,
                ],
            ),
            expand=True,
            **kwargs,
        )
