Write-Host "Checking for Docker images..."
$images = docker images --format "{{.Repository}}:{{.Tag}}" | Where-Object { $_ -ne "<none>:<none>" }

if ($images) {
    Write-Host "Found $($images.Count) images. Starting backup..."
    Write-Host "This might take a few minutes. Please wait..."
    docker save -o docker_images_backup.tar $images
    Write-Host "========================================="
    Write-Host "✅ Backup complete!"
    Write-Host "All your images have been safely stored in: docker_images_backup.tar"
    Write-Host "If you ever accidentally prune your images, you can restore them by running:"
    Write-Host "docker load -i docker_images_backup.tar"
    Write-Host "========================================="
} else {
    Write-Host "No Docker images found. Make sure Docker is running and you have images pulled."
}
