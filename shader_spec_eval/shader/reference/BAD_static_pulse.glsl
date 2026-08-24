void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    // Radial and blue and symmetric, but ignores iTime -> must fail `animates`.
    vec2 uv = (fragCoord - 0.5 * iResolution.xy) / iResolution.y;
    float i = exp(-length(uv) * length(uv) * 7.0);
    fragColor = vec4(vec3(0.12, 0.30, 1.0) * i, 1.0);
}
