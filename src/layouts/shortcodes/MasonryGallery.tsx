import React from "react";

type Props = {
  images: string[];
  className?: string;
  columns?: number;
  mdColumns?: number;
  alt?: string;
};

const MasonryGallery: React.FC<Props> = ({
  images = [],
  className = "",
  columns = 2,
  mdColumns = 3,
  alt = "Gallery image",
}) => {
  const containerClass = `columns-${columns} md:columns-${mdColumns} gap-4 ${className}`;

  return (
    <div className={containerClass}>
      {images?.map((src, index) => (
        <figure
          key={`${src}-${index}`}
          className="group mb-4 break-inside-avoid overflow-hidden rounded-xl bg-white shadow-md hover:shadow-lg transition-shadow duration-300"
        >
          <img
            src={src}
            alt={`${alt} ${index + 1}`}
            className="w-full h-auto block"
            loading="lazy"
          />
        </figure>
      ))}
    </div>
  );
};

export default MasonryGallery;
