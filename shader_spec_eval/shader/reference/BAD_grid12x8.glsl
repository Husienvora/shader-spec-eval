void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    float c = mod(floor(uv.x * 12.0) + floor(uv.y * 8.0), 2.0);
    fragColor = vec4(mix(vec3(0.015), vec3(1.0, 0.9, 0.05), c), 1.0);
}
