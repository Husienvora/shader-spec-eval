void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    // Gradient runs vertically, not left-to-right -> must fail gradient_along x.
    vec2 uv = fragCoord / iResolution.xy;
    fragColor = vec4(vec3(0.15 + 0.85 * uv.y, 0.06, 0.05), 1.0);
}
