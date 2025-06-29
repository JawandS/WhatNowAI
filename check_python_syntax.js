const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

function findPythonFiles(dir) {
  const pythonFiles = [];
  
  function searchDirectory(currentDir) {
    try {
      const items = fs.readdirSync(currentDir);
      
      for (const item of items) {
        const fullPath = path.join(currentDir, item);
        const stat = fs.statSync(fullPath);
        
        if (stat.isDirectory()) {
          // Skip common directories that don't contain source code
          if (!['node_modules', '.git', '__pycache__', '.venv', 'venv'].includes(item)) {
            searchDirectory(fullPath);
          }
        } else if (stat.isFile() && item.endsWith('.py')) {
          pythonFiles.push(fullPath);
        }
      }
    } catch (error) {
      console.warn(`Warning: Could not read directory ${currentDir}: ${error.message}`);
    }
  }
  
  searchDirectory(dir);
  return pythonFiles;
}

function checkPythonSyntax() {
  console.log('Checking Python syntax...');
  
  const pythonFiles = findPythonFiles('.');
  
  if (pythonFiles.length === 0) {
    console.log('No Python files found.');
    return;
  }
  
  console.log(`Found ${pythonFiles.length} Python files to check:`);
  
  let hasErrors = false;
  
  for (const file of pythonFiles) {
    try {
      console.log(`Checking ${file}...`);
      execSync(`python -m py_compile "${file}"`, { stdio: 'pipe' });
      console.log(`✓ ${file} - OK`);
    } catch (error) {
      console.error(`✗ ${file} - SYNTAX ERROR:`);
      console.error(error.stderr.toString());
      hasErrors = true;
    }
  }
  
  if (hasErrors) {
    console.log('\nSyntax check completed with errors.');
    process.exit(1);
  } else {
    console.log('\nAll Python files passed syntax check.');
  }
}

checkPythonSyntax();