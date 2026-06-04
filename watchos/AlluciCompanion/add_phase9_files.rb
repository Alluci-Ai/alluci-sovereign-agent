require 'xcodeproj'

project_path = '/Users/alluci/Downloads/alluci-sovereign-agent-main/watchos/AlluciCompanion/AlluciCompanion.xcodeproj'
project = Xcodeproj::Project.open(project_path)
target = project.targets.find { |t| t.name == 'AlluciCompanion' }

managers_group = project.main_group.find_subpath('AlluciCompanion/Managers', true)
views_group = project.main_group.find_subpath('AlluciCompanion/Views', true)

# Remove existing references if any
managers_group.files.each { |f| f.remove_from_project if ['HealthKitManager.swift', 'VoiceManager.swift'].include?(f.path) }
views_group.files.each { |f| f.remove_from_project if f.path == 'PVTView.swift' }

# Add HealthKitManager
hk_ref = managers_group.new_file('Managers/HealthKitManager.swift')
hk_ref.set_path('Managers/HealthKitManager.swift')
hk_ref.source_tree = '<group>'

# Add VoiceManager
vm_ref = managers_group.new_file('Managers/VoiceManager.swift')
vm_ref.set_path('Managers/VoiceManager.swift')
vm_ref.source_tree = '<group>'

# Add PVTView
pvt_ref = views_group.new_file('Views/PVTView.swift')
pvt_ref.set_path('Views/PVTView.swift')
pvt_ref.source_tree = '<group>'

target.add_file_references([hk_ref, vm_ref, pvt_ref])
project.save

puts "Added Phase 9 files to project"
