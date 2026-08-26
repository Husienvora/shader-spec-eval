void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    ivec2 cell = ivec2(floor(fragCoord / iResolution.xy * 8.0));
    float parity = float((cell.x + cell.y) & 1);
    fragColor = vec4(mix(vec3(0.01), vec3(0.08, 0.95, 0.16), parity), 1.0);
}
