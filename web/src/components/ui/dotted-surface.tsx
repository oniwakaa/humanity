'use client';
import { cn } from '@/lib/utils';
import { useTheme } from 'next-themes';
import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

type DottedSurfaceProps = Omit<React.ComponentProps<'div'>, 'ref'>;

export function DottedSurface({ className, ...props }: DottedSurfaceProps) {
	const { resolvedTheme } = useTheme();
	const containerRef = useRef<HTMLDivElement>(null);
	const cleanupRef = useRef<(() => void) | null>(null);

	useEffect(() => {
		// Prevent double initialization in Strict Mode
		if (cleanupRef.current) {
			cleanupRef.current();
			cleanupRef.current = null;
		}

		const container = containerRef.current;
		if (!container) return;

		// Configuration
		const SEPARATION = 100;
		const AMOUNTX = 50;
		const AMOUNTY = 50;

		// Scene
		const scene = new THREE.Scene();

		// Camera
		const camera = new THREE.PerspectiveCamera(
			75,
			window.innerWidth / window.innerHeight,
			1,
			10000
		);
		camera.position.z = 1000;
		camera.position.y = 400;
		camera.lookAt(0, 0, 0);

		// Renderer
		let renderer: THREE.WebGLRenderer;
		try {
			renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
			renderer.setPixelRatio(window.devicePixelRatio);
			renderer.setSize(window.innerWidth, window.innerHeight);
			renderer.setClearColor(0x000000, 0);
			container.appendChild(renderer.domElement);
		} catch (error) {
			console.warn('WebGL Context not available:', error);
			return;
		}

		// Particles
		const numParticles = AMOUNTX * AMOUNTY;
		const positions = new Float32Array(numParticles * 3);
		const colors = new Float32Array(numParticles * 3);

		// Determine color based on theme
		const isDark = resolvedTheme === 'dark' ||
			(resolvedTheme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches) ||
			resolvedTheme === undefined; // Default to dark if theme not resolved yet

		const dotColor = isDark ? new THREE.Color(0x888888) : new THREE.Color(0x333333);

		let idx = 0;
		for (let ix = 0; ix < AMOUNTX; ix++) {
			for (let iy = 0; iy < AMOUNTY; iy++) {
				positions[idx * 3] = ix * SEPARATION - (AMOUNTX * SEPARATION) / 2;
				positions[idx * 3 + 1] = 0;
				positions[idx * 3 + 2] = iy * SEPARATION - (AMOUNTY * SEPARATION) / 2;

				colors[idx * 3] = dotColor.r;
				colors[idx * 3 + 1] = dotColor.g;
				colors[idx * 3 + 2] = dotColor.b;
				idx++;
			}
		}

		const geometry = new THREE.BufferGeometry();
		geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
		geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

		const material = new THREE.PointsMaterial({
			size: 5,
			vertexColors: true,
			transparent: true,
			opacity: 0.7,
		});

		const particles = new THREE.Points(geometry, material);
		scene.add(particles);

		// Animation state
		let animationFrameId: number;
		let isRunning = true;

		const animate = () => {
			if (!isRunning) return;

			animationFrameId = requestAnimationFrame(animate);

			const time = Date.now() * 0.0005; // Slow time factor
			const posArray = geometry.attributes.position.array as Float32Array;

			let i = 0;
			for (let ix = 0; ix < AMOUNTX; ix++) {
				for (let iy = 0; iy < AMOUNTY; iy++) {
					// Wave animation on Y axis
					posArray[i * 3 + 1] =
						Math.sin((ix + time * 10) * 0.3) * 50 +
						Math.sin((iy + time * 10) * 0.5) * 50;
					i++;
				}
			}

			geometry.attributes.position.needsUpdate = true;
			renderer.render(scene, camera);
		};

		// Handle resize
		const handleResize = () => {
			camera.aspect = window.innerWidth / window.innerHeight;
			camera.updateProjectionMatrix();
			renderer.setSize(window.innerWidth, window.innerHeight);
		};

		window.addEventListener('resize', handleResize);
		animate();

		// Cleanup function
		const cleanup = () => {
			isRunning = false;
			cancelAnimationFrame(animationFrameId);
			window.removeEventListener('resize', handleResize);

			geometry.dispose();
			material.dispose();
			renderer.dispose();

			if (container.contains(renderer.domElement)) {
				container.removeChild(renderer.domElement);
			}
		};

		cleanupRef.current = cleanup;

		return cleanup;
	}, [resolvedTheme]);

	return (
		<div
			ref={containerRef}
			className={cn('pointer-events-none fixed inset-0 z-0', className)}
			{...props}
		/>
	);
}
